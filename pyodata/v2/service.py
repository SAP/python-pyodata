"""OData service implementation

   Details regarding batch requests and changesets:
   http://www.odata.org/documentation/odata-version-2-0/batch-processing/
"""

# pylint: disable=too-many-lines

import logging
from functools import partial
import json
import random
from email.parser import Parser
from http.client import HTTPResponse
from io import BytesIO
from urllib.parse import urlencode


from pyodata.exceptions import HttpError, PyODataException, ExpressionError, ProgramError
from . import model

LOGGER_NAME = 'pyodata.service'

HTTP_CODE_OK = 200
HTTP_CODE_CREATED = 201


def urljoin(*path):
    """Joins the passed string parts into a one string url"""

    return '/'.join((part.strip('/') for part in path))


def encode_multipart(boundary, http_requests):
    """Encode list of requests into multipart body"""

    lines = []

    lines.append('')

    for req in http_requests:

        lines.append(f'--{boundary}')

        if not isinstance(req, MultipartRequest):
            lines.extend(('Content-Type: application/http ', 'Content-Transfer-Encoding:binary'))

            lines.append('')

            # request  line (method + path + query params)
            line = f'{req.get_method()} {req.get_path()}'
            query_params = urlencode(req.get_query_params())
            if query_params:
                line += '?' + query_params
            line += ' HTTP/1.1'

            lines.append(line)

        # request specific headers
        for hdr, hdr_val in req.get_headers().items():
            lines.append(f'{hdr}: {hdr_val}')

        lines.append('')

        body = req.get_body()
        if body is not None:
            lines.append(req.get_body())
        else:
            # this is very important since SAP gateway rejected request witout this line. It seems
            # blank line must be provided as a representation of emtpy body, else we are getting
            # 400 Bad fromat from SAP gateway
            lines.append('')

    lines.append(f'--{boundary}--')

    return '\r\n'.join(lines)


def decode_multipart(data, content_type):
    """Decode parts of the multipart mime content"""

    def decode(message):
        """Decode tree of messages for specific message"""

        messages = []
        for i, part in enumerate(message.walk()):  # pylint: disable=unused-variable
            if part.get_content_type() == 'multipart/mixed':
                for submessage in part.get_payload():
                    messages.append(decode(submessage))
                break
            messages.append(part.get_payload())
        return messages

    data = f"Content-Type: {content_type}\n" + data
    parser = Parser()
    parsed = parser.parsestr(data)
    decoded = decode(parsed)

    return decoded


class ODataHttpResponse:
    """Representation of http response"""

    def __init__(self, headers, status_code, content=None, url=None):
        self.url = url
        self.headers = headers
        self.status_code = status_code
        self.content = content

    @staticmethod
    def from_string(data):
        """Parse http response to status code, headers and body

            Based on: https://stackoverflow.com/questions/24728088/python-parse-http-response-string
        """

        class FakeSocket:
            """Fake socket to simulate received http response content"""

            def __init__(self, response_str):
                self._file = BytesIO(response_str.encode('utf-8'))

            def makefile(self, *args, **kwargs):
                """Fake file that provides string content"""
                # pylint: disable=unused-argument

                return self._file

        source = FakeSocket(data)
        response = HTTPResponse(source)
        response.begin()
        response.length = response.fp.__sizeof__()

        return ODataHttpResponse(
            dict(response.getheaders()),
            response.status,
            response.read(len(data))  # the len here will give a 'big enough' value to read the whole content
        )

    def json(self):
        """Return response as decoded json"""

        # TODO: see implementation in python requests, our simple
        # approach can bring issues with encoding
        # https://github.com/requests/requests/blob/master/requests/models.py#L868
        if self.content:
            return json.loads(self.content.decode('utf-8'))
        return None


class EntityKey:
    """An immutable entity-key, made up of either a single value (single)
       or multiple key-value pairs (complex).

      Every entity must have an entity-key. The entity-key must be unique
      within the entity-set, and thus defines an entity's identity.

      The string representation of an entity-key is wrapped with parentheses,
      such as (2), ('foo') or (a=1,foo='bar').

      Entity-keys are equal if their string representations are equal.
    """

    TYPE_SINGLE = 0
    TYPE_COMPLEX = 1

    def __init__(self, entity_type, single_key=None, **args):

        self._logger = logging.getLogger(LOGGER_NAME)
        self._proprties = args
        self._entity_type = entity_type
        self._key = entity_type.key_proprties

        # single key does not need property name
        if single_key is not None:

            # check that entity type key consists of exactly one property
            if len(self._key) != 1:
                raise PyODataException(('Key of entity type {} consists of multiple properties {} '
                                        'and cannot be initialized by single value').format(
                                            self._entity_type.name, ', '.join([prop.name for prop in self._key])))

            # get single key property and format key string
            key_prop = self._key[0]
            args[key_prop.name] = single_key

            self._type = EntityKey.TYPE_SINGLE

            self._logger.debug(('Detected single property key, adding pair %s->%s to key'
                                'properties'), key_prop.name, single_key)
        else:
            for key_prop in self._key:
                if key_prop.name not in args:
                    raise PyODataException(f'Missing value for key property {key_prop.name}')

            self._type = EntityKey.TYPE_COMPLEX

    @property
    def key_properties(self):
        """Key properties"""

        return self._key

    def to_key_string_without_parentheses(self):
        """Gets the string representation of the key without parentheses"""

        if self._type == EntityKey.TYPE_SINGLE:
            # first property is the key property
            key_prop = self._key[0]
            return key_prop.to_literal(self._proprties[key_prop.name])

        key_pairs = []
        for key_prop in self._key:
            # if key_prop.name not in self.__dict__['_cache']:
            #    raise RuntimeError('Entity key is not complete, missing value of property: {0}'.format(key_prop.name))

            key_pairs.append(
                f'{key_prop.name}={key_prop.to_literal(self._proprties[key_prop.name])}')

        return ','.join(key_pairs)

    def to_key_string(self):
        """Gets the string representation of the key, including parentheses"""

        return f'({self.to_key_string_without_parentheses()})'

    def __repr__(self):
        return self.to_key_string()


class ODataHttpRequest:
    """Deferred HTTP Request"""

    def __init__(self, url, connection, handler, headers=None):
        self._connection = connection
        self._url = url
        self._handler = handler
        self._headers = headers or dict()
        self._logger = logging.getLogger(LOGGER_NAME)
        self._customs = {}  # string -> string hash
        self._next_url = None

    @property
    def handler(self):
        """Getter for handler"""
        return self._handler

    def get_path(self):
        """Get path of the HTTP request"""
        # pylint: disable=no-self-use
        return ''

    def get_query_params(self):
        """Get query params"""
        # pylint: disable=no-self-use
        return dict(self._customs)

    def get_method(self):
        """Get HTTP method"""
        # pylint: disable=no-self-use
        return 'GET'

    def get_body(self):
        """Get HTTP body or None if not applicable"""
        # pylint: disable=no-self-use
        return None

    def get_default_headers(self):
        """Get dict of Child specific HTTP headers"""
        # pylint: disable=no-self-use
        return dict()

    def get_headers(self):
        """Get dict of HTTP headers which is union of return value
           of the method get_default_headers() and the headers
           added via the method add_headers() where the latter
           headers have priority - same keys get value of the latter.
        """

        headers = self.get_default_headers()
        headers.update(self._headers)

        return headers

    def add_headers(self, value):
        """Add the give dictionary of HTTP headers to
           HTTP request sent by this ODataHttpRequest instance.
        """

        if not isinstance(value, dict):
            raise TypeError(f"Headers must be of type 'dict' not {type(value)}")

        self._headers.update(value)

    def _build_request(self):
        if self._next_url:
            url = self._next_url
        else:
            url = urljoin(self._url, self.get_path())
        # pylint: disable=assignment-from-none
        body = self.get_body()

        headers = self.get_headers()

        self._logger.debug('Send (execute) %s request to %s', self.get_method(), url)
        self._logger.debug('  query params: %s', self.get_query_params())
        self._logger.debug('  headers: %s', headers)
        if body:
            self._logger.debug('  body: %s', body)

        params = self.get_query_params()

        return url, body, headers, params

    async def async_execute(self):
        """Fetches HTTP response and returns processed result

                  Sends the query-request to the OData service, returning a client-side Enumerable for
                  subsequent in-memory operations.

                  Fetches HTTP response and returns processed result"""

        url, body, headers, params = self._build_request()
        async with self._connection.request(self.get_method(),
                                            url,
                                            headers=headers,
                                            params=params,
                                            data=body) as async_response:
            response = ODataHttpResponse(url=async_response.url,
                                         headers=async_response.headers,
                                         status_code=async_response.status,
                                         content=await async_response.read())
        return self._call_handler(response)

    def execute(self):
        """Fetches HTTP response and returns processed result

           Sends the query-request to the OData service, returning a client-side Enumerable for
           subsequent in-memory operations.

           Fetches HTTP response and returns processed result"""

        url, body, headers, params = self._build_request()

        response = self._connection.request(
            self.get_method(), url, headers=headers, params=urlencode(params), data=body)

        return self._call_handler(response)

    def _call_handler(self, response):
        self._logger.debug('Received response')
        self._logger.debug('  url: %s', response.url)
        self._logger.debug('  headers: %s', response.headers)
        self._logger.debug('  status code: %d', response.status_code)

        try:
            self._logger.debug('  body: %s', response.content.decode('utf-8'))
        except UnicodeDecodeError:
            self._logger.debug('  body: <cannot be decoded>')

        return self._handler(response)

    def custom(self, name, value):
        """Adds a custom name-value pair."""
        # returns QueryRequest
        self._customs[name] = value
        return self


class EntityGetRequest(ODataHttpRequest):
    """Used for GET operations of a single entity"""

    def __init__(self, handler, entity_key, entity_set_proxy):
        super(EntityGetRequest, self).__init__(entity_set_proxy.service.url, entity_set_proxy.service.connection,
                                               handler)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._entity_key = entity_key
        self._entity_set_proxy = entity_set_proxy
        self._select = None
        self._expand = None

        self._logger.debug('New instance of EntityGetRequest for last segment: %s', self._entity_set_proxy.last_segment)

    def nav(self, nav_property):
        """Navigates to given navigation property and returns the EntitySetProxy"""
        return self._entity_set_proxy.nav(nav_property, self._entity_key)

    def select(self, select):
        """Specifies a subset of properties to return.

           @param select  a comma-separated list of selection clauses
        """
        self._select = select
        return self

    def expand(self, expand):
        """Specifies related entities to expand inline as part of the response.

           @param expand  a comma-separated list of navigation properties
        """
        self._expand = expand
        return self

    def get_path(self):
        return self._entity_set_proxy.last_segment + self._entity_key.to_key_string()

    def get_default_headers(self):
        return {'Accept': 'application/json'}

    def get_query_params(self):
        qparams = super(EntityGetRequest, self).get_query_params()

        if self._select is not None:
            qparams['$select'] = self._select

        if self._expand is not None:
            qparams['$expand'] = self._expand

        return qparams

    def get_value(self, connection=None):
        """Returns Value of Media EntityTypes also known as the $value URL suffix."""

        if connection is None:
            connection = self._connection

        def stream_handler(response):
            """Returns $value from HTTP Response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for $value failed with status code {}'
                                .format(response.status_code), response)

            return response

        return ODataHttpRequest(
            urljoin(self._url, self.get_path(), '/$value'),
            connection,
            stream_handler)


class NavEntityGetRequest(EntityGetRequest):
    """Used for GET operations of a single entity accessed via a Navigation property"""

    def __init__(self, handler, master_key, entity_set_proxy, nav_property):
        super(NavEntityGetRequest, self).__init__(handler, master_key, entity_set_proxy)

        self._nav_property = nav_property

    def get_path(self):
        return f"{super(NavEntityGetRequest, self).get_path()}/{self._nav_property}"


class EntityCreateRequest(ODataHttpRequest):
    """Used for creating entities (POST operations of a single entity)

       Call execute() to send the create-request to the OData service
       and get the newly created entity."""

    def __init__(self, url, connection, handler, entity_set, last_segment=None):
        super(EntityCreateRequest, self).__init__(url, connection, handler)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._entity_set = entity_set
        self._entity_type = entity_set.entity_type

        if last_segment is None:
            self._last_segment = self._entity_set.name
        else:
            self._last_segment = last_segment

        self._values = {}

        # get all properties declared by entity type
        self._type_props = self._entity_type.proprties()

        self._logger.debug('New instance of EntityCreateRequest for entity type: %s on path %s', self._entity_type.name,
                           self._last_segment)

    def get_path(self):
        return self._last_segment

    def get_method(self):
        # pylint: disable=no-self-use
        return 'POST'

    def _get_body(self):
        """Recursively builds a dictionary of values where some of the values
           might be another entities.
        """

        body = {}
        for key, val in self._values.items():
            # The value is either an entity or a scalar
            if isinstance(val, EntityProxy):
                body[key] = val._get_body()  # pylint: disable=protected-access
            else:
                body[key] = val

        return body

    def get_body(self):
        return json.dumps(self._get_body())

    def get_default_headers(self):
        return {'Accept': 'application/json', 'Content-Type': 'application/json', 'X-Requested-With': 'X'}

    @staticmethod
    def _build_values(entity_type, entity):
        """Recursively converts a dictionary of values where some of the values
           might be another entities (navigation properties) into the internal
           representation.
        """

        if isinstance(entity, list):
            return [EntityCreateRequest._build_values(entity_type, item) for item in entity]

        values = {}
        for key, val in entity.items():
            try:
                val = entity_type.proprty(key).to_json(val)
            except KeyError:
                try:
                    nav_prop = entity_type.nav_proprty(key)
                    val = EntityCreateRequest._build_values(nav_prop.typ, val)
                except KeyError:
                    raise PyODataException('Property {} is not declared in {} entity type'.format(
                        key, entity_type.name))

            values[key] = val

        return values

    def set(self, **kwargs):
        """Set properties on the new entity."""

        self._logger.info(kwargs)

        # TODO: consider use of attset for setting properties
        self._values = EntityCreateRequest._build_values(self._entity_type, kwargs)

        return self


class EntityDeleteRequest(ODataHttpRequest):
    """Used for deleting entity (DELETE operations on a single entity)"""

    def __init__(self, url, connection, handler, entity_set, entity_key):
        super(EntityDeleteRequest, self).__init__(url, connection, handler)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._entity_set = entity_set
        self._entity_key = entity_key

        self._logger.debug('New instance of EntityDeleteRequest for entity type: %s', entity_set.entity_type.name)

    def get_path(self):
        return self._entity_set.name + self._entity_key.to_key_string()

    def get_method(self):
        # pylint: disable=no-self-use
        return 'DELETE'


class EntityModifyRequest(ODataHttpRequest):
    """Used for modyfing entities (UPDATE/MERGE operations on a single entity)

       Call execute() to send the update-request to the OData service
       and get the modified entity."""

    ALLOWED_HTTP_METHODS = ['PATCH', 'PUT', 'MERGE']

    def __init__(self, url, connection, handler, entity_set, entity_key, method="PATCH"):
        super(EntityModifyRequest, self).__init__(url, connection, handler)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._entity_set = entity_set
        self._entity_type = entity_set.entity_type
        self._entity_key = entity_key

        self._method = method.upper()
        if self._method not in EntityModifyRequest.ALLOWED_HTTP_METHODS:
            raise ValueError('The value "{}" is not on the list of allowed Entity Update HTTP Methods: {}'
                             .format(method, ', '.join(EntityModifyRequest.ALLOWED_HTTP_METHODS)))

        self._values = {}

        # get all properties declared by entity type
        self._type_props = self._entity_type.proprties()

        self._logger.debug('New instance of EntityModifyRequest for entity type: %s', self._entity_type.name)

    def get_path(self):
        return self._entity_set.name + self._entity_key.to_key_string()

    def get_method(self):
        # pylint: disable=no-self-use
        return self._method

    def get_body(self):
        # pylint: disable=no-self-use
        body = {}
        for key, val in self._values.items():
            body[key] = val
        return json.dumps(body)

    def get_default_headers(self):
        return {'Accept': 'application/json', 'Content-Type': 'application/json'}

    def set(self, **kwargs):
        """Set properties to be changed."""

        self._logger.info(kwargs)

        for key, val in kwargs.items():
            try:
                val = self._entity_type.proprty(key).to_json(val)
            except KeyError:
                raise PyODataException(
                    f'Property {key} is not declared in {self._entity_type.name} entity type')

            self._values[key] = val

        return self


class QueryRequest(ODataHttpRequest):
    """INTERFACE A consumer-side query-request builder. Call execute() to issue the request."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, url, connection, handler, last_segment):
        super(QueryRequest, self).__init__(url, connection, handler)

        self._logger = logging.getLogger(LOGGER_NAME)
        self._count = None
        self._inlinecount = None
        self._top = None
        self._skip = None
        self._order_by = None
        self._filter = None
        self._select = None
        self._expand = None
        self._last_segment = last_segment
        self._logger.debug('New instance of QueryRequest for last segment: %s', self._last_segment)

    def count(self, inline=False):
        """Sets a flag to return the number of items. Can be inline with results or just the count."""
        if inline:
            self._inlinecount = True
        else:
            self._count = True
        return self

    def next_url(self, next_url):
        """
        Sets URL which identifies the next partial set of entities from the originally identified complete set. Once
        set, this URL takes precedence over all query parameters.

        For details, see section "6. Representing Collections of Entries" on
        https://www.odata.org/documentation/odata-version-2-0/json-format/
        """
        self._next_url = next_url
        return self

    def expand(self, expand):
        """Sets the expand expressions."""
        self._expand = expand
        return self

    def filter(self, filter_val):
        """Sets the filter expression."""
        # returns QueryRequest
        self._filter = filter_val
        return self

    # def nav(self, key_value, nav_property):
    #    """Navigates to a referenced collection using a collection-valued navigation property."""
    #    # returns QueryRequest
    #    raise NotImplementedError

    def order_by(self, order_by):
        """Sets the ordering expressions."""
        self._order_by = order_by
        return self

    def select(self, select):
        """Sets the selection clauses."""
        self._select = select
        return self

    def skip(self, skip):
        """Sets the number of items to skip."""
        self._skip = skip
        return self

    def top(self, top):
        """Sets the number of items to return."""
        self._top = top
        return self

    def get_path(self):
        if self._count:
            return urljoin(self._last_segment, '/$count')

        return self._last_segment

    def get_default_headers(self):
        if self._count:
            return {}

        return {
            'Accept': 'application/json',
        }

    def get_query_params(self):
        if self._next_url:
            return {}

        qparams = super(QueryRequest, self).get_query_params()

        if self._top is not None:
            qparams['$top'] = self._top

        if self._skip is not None:
            qparams['$skip'] = self._skip

        if self._order_by is not None:
            qparams['$orderby'] = self._order_by

        if self._filter is not None:
            qparams['$filter'] = self._filter

        if self._select is not None:
            qparams['$select'] = self._select

        if self._expand is not None:
            qparams['$expand'] = self._expand

        if self._inlinecount:
            qparams['$inlinecount'] = 'allpages'

        return qparams


class FunctionRequest(QueryRequest):
    """Function import request (Service call)"""

    def __init__(self, url, connection, handler, function_import):
        super(FunctionRequest, self).__init__(url, connection, handler, function_import.name)

        self._function_import = function_import

        self._logger.debug('New instance of FunctionRequest for %s', self._function_import.name)

    def parameter(self, name, value):
        '''Sets value of parameter.'''

        # check if param is valid (is declared in metadata)
        try:
            param = self._function_import.get_parameter(name)

            # add parameter as custom query argument
            self.custom(param.name, param.to_literal(value))
        except KeyError:
            raise PyODataException('Function import {0} does not have pararmeter {1}'
                                   .format(self._function_import.name, name))

        return self

    def get_method(self):
        return self._function_import.http_method

    def get_default_headers(self):
        return {
            'Accept': 'application/json'
        }


# pylint: disable=too-many-instance-attributes
class EntityProxy:
    """An immutable OData entity instance, consisting of an identity (an
       entity-set and a unique entity-key within that set), properties (typed,
       named values), and links (references to other entities).
    """

    # pylint: disable=too-many-branches,too-many-nested-blocks,too-many-statements

    def __init__(self, service, entity_set, entity_type, proprties=None, entity_key=None, etag=None):
        self._logger = logging.getLogger(LOGGER_NAME)
        self._service = service
        self._entity_set = entity_set
        self._entity_type = entity_type
        self._key_props = entity_type.key_proprties
        self._cache = dict()
        self._entity_key = entity_key
        self._etag = etag

        self._logger.debug('New entity proxy instance of type %s from properties: %s', entity_type.name, proprties)

        # cache values of individual properties if provided
        if proprties is not None:

            etag_body = proprties.get('__metadata', dict()).get('etag', None)
            if etag is not None and etag_body is not None and etag_body != etag:
                raise PyODataException('Etag from header does not match the Etag from response body')

            if etag_body is not None:
                self._etag = etag_body

            # first, cache values of direct properties
            for type_proprty in self._entity_type.proprties():
                if type_proprty.name in proprties:
                    # Property value available
                    if proprties[type_proprty.name] is not None:
                        self._cache[type_proprty.name] = type_proprty.from_json(proprties[type_proprty.name])
                        continue
                    # Property value missing and user wants a type specific default value filled in
                    if not self._service.retain_null:
                        # null value is in literal form for now, convert it to python representation
                        self._cache[type_proprty.name] = type_proprty.from_literal(type_proprty.typ.null_value)
                        continue
                    # Property is nullable - save it as such
                    if type_proprty.nullable:
                        self._cache[type_proprty.name] = None
                        continue
                    raise PyODataException(f'Value of non-nullable Property {type_proprty.name} is null')

            # then, assign all navigation properties
            for prop in self._entity_type.nav_proprties:

                if prop.name in proprties:

                    # entity type of navigation property
                    prop_etype = prop.to_role.entity_type

                    # cache value according to multiplicity
                    if prop.to_role.multiplicity in \
                            [model.EndRole.MULTIPLICITY_ONE,
                             model.EndRole.MULTIPLICITY_ZERO_OR_ONE]:

                        # cache None in case we receive nothing (null) instead of entity data
                        if proprties[prop.name] is None:
                            self._cache[prop.name] = None
                        else:
                            self._cache[prop.name] = EntityProxy(service, None, prop_etype, proprties[prop.name])

                    elif prop.to_role.multiplicity == model.EndRole.MULTIPLICITY_ZERO_OR_MORE:
                        # default value is empty array
                        self._cache[prop.name] = []

                        # if there are no entities available, received data consists of
                        # metadata properties only.
                        if 'results' in proprties[prop.name]:

                            # available entities are serialized in results array
                            for entity in proprties[prop.name]['results']:
                                self._cache[prop.name].append(EntityProxy(service, None, prop_etype, entity))
                    else:
                        raise PyODataException('Unknown multiplicity {0} of association role {1}'
                                               .format(prop.to_role.multiplicity, prop.to_role.name))

        # build entity key if not provided
        if self._entity_key is None:
            # try to build key from available property values
            try:
                # if key seems to be simple (consists of single property)
                if len(self._key_props) == 1:
                    self._entity_key = EntityKey(entity_type, self._cache[self._key_props[0].name])
                else:
                    # build complex key
                    self._entity_key = EntityKey(entity_type, **self._cache)
            except KeyError:
                pass
            except PyODataException:
                pass

    def __repr__(self):
        return self._entity_key.to_key_string()

    def __getattr__(self, attr):
        try:
            return self._cache[attr]
        except KeyError:
            try:
                value = self.get_proprty(attr).execute()
                self._cache[attr] = value
                return value
            except KeyError as ex:
                raise AttributeError('EntityType {0} does not have Property {1}: {2}'
                                     .format(self._entity_type.name, attr, str(ex)))

    async def async_getattr(self, attr):
        """Get cached value of attribute or do async call to service to recover attribute value"""
        try:
            return self._cache[attr]
        except KeyError:
            try:
                value = await self.get_proprty(attr).async_execute()
                self._cache[attr] = value
                return value
            except KeyError as ex:
                raise AttributeError('EntityType {0} does not have Property {1}: {2}'
                                     .format(self._entity_type.name, attr, str(ex)))

    def nav(self, nav_property):
        """Navigates to given navigation property and returns the EntitySetProxy"""

        # for now duplicated with simillar method in entity set proxy class
        try:
            navigation_property = self._entity_type.nav_proprty(nav_property)
        except KeyError:
            raise PyODataException('Navigation property {} is not declared in {} entity type'.format(
                nav_property, self._entity_type))

        # Get entity set of navigation property
        association_info = navigation_property.association_info
        association_set = self._service.schema.association_set_by_association(
            association_info.name,
            association_info.namespace)

        end = association_set.end_by_role(navigation_property.to_role.role)
        navigation_entity_set = self._service.schema.entity_set(end.entity_set_name)

        if navigation_property.to_role.multiplicity != model.EndRole.MULTIPLICITY_ZERO_OR_MORE:
            return self._get_nav_entity(nav_property, navigation_entity_set)

        return EntitySetProxy(
            self._service,
            self._service.schema.entity_set(navigation_entity_set.name),
            nav_property,
            self._entity_set.name + self._entity_key.to_key_string())

    def _get_nav_entity(self, nav_property, navigation_entity_set):
        """Get entity based on Navigation property name"""

        def get_entity_handler(parent, nav_property, navigation_entity_set, response):
            """Gets entity from HTTP response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Entity {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity = response.json()['d']

            return NavEntityProxy(parent, nav_property, navigation_entity_set.entity_type, entity)

        self._logger.info(
            'Getting the nav property %s of the entity %s for the key %s',
            nav_property,
            self._entity_set,
            self.entity_key)

        return NavEntityGetRequest(
            partial(get_entity_handler, self, nav_property, navigation_entity_set),
            self.entity_key,
            getattr(self._service.entity_sets, self.entity_set.name),
            nav_property)

    def get_path(self):
        """Returns this entity's relative path - e.g. EntitySet(KEY)"""

        return self._entity_set._name + self._entity_key.to_key_string()  # pylint: disable=protected-access

    def get_proprty(self, name, connection=None):
        """Returns value of the property"""

        self._logger.info('Initiating property request for %s', name)

        def proprty_get_handler(key, proprty, response):
            """Gets property value from HTTP Response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Attribute {0} of Entity {1} failed with status code {2}'
                                .format(proprty.name, key, response.status_code), response)

            data = response.json()['d']
            return proprty.from_json(data[proprty.name])

        path = urljoin(self.get_path(), name)
        return self._service.http_get_odata(
            path,
            partial(proprty_get_handler, path, self._entity_type.proprty(name)),
            connection=connection)

    def get_value(self, connection=None):
        "Returns $value of Stream entities"

        def value_get_handler(key, response):
            """Gets property value from HTTP Response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for $value of Entity {0} failed with status code {1}'
                                .format(key, response.status_code), response)

            return response

        path = urljoin(self.get_path(), '/$value')
        return self._service.http_get_odata(path,
                                            partial(value_get_handler, self.entity_key),
                                            connection=connection)

    @property
    def entity_set(self):
        """Entity set related to this entity"""

        return self._entity_set

    @property
    def entity_key(self):
        """Key of entity"""

        return self._entity_key

    @property
    def url(self):
        """URL of the real entity"""

        service_url = self._service.url.rstrip('/')
        entity_path = self.get_path()

        return urljoin(service_url, entity_path)

    @property
    def etag(self):
        """ETag generated by service"""
        return self._etag

    def equals(self, other):
        """Returns true if the self and the other contains the same data"""
        # pylint: disable=W0212
        return self._cache == other._cache


class NavEntityProxy(EntityProxy):
    """Special case of an Entity access via 1 to 1 Navigation property"""

    def __init__(self, parent_entity, prop_name, entity_type, entity):
        # pylint: disable=protected-access
        super(NavEntityProxy, self).__init__(parent_entity._service, parent_entity._entity_set, entity_type, entity)

        self._parent_entity = parent_entity
        self._prop_name = prop_name

    def get_path(self):
        """Returns URL of the entity"""

        return urljoin(self._parent_entity.get_path(), self._prop_name)


class GetEntitySetFilter:
    """Create filters for humans"""

    def __init__(self, proprty):
        self._proprty = proprty

    @staticmethod
    def build_expression(operator, operands):
        """Creates a expression by joining the operands with the operator"""

        if len(operands) < 2:
            raise ExpressionError('The $filter operator \'{}\' needs at least two operands'.format(operator))

        return f"({' {} '.format(operator).join(operands)})"

    @staticmethod
    def and_(*operands):
        """Creates logical AND expression from the operands"""

        return GetEntitySetFilter.build_expression('and', operands)

    @staticmethod
    def or_(*operands):
        """Creates logical OR expression from the operands"""

        return GetEntitySetFilter.build_expression('or', operands)

    @staticmethod
    def format_filter(proprty, operator, value):
        """Creates a filter expression """

        return f'{proprty.name} {operator} {proprty.to_literal(value)}'

    def __eq__(self, value):
        return GetEntitySetFilter.format_filter(self._proprty, 'eq', value)

    def __ne__(self, value):
        return GetEntitySetFilter.format_filter(self._proprty, 'ne', value)

    def __lt__(self, value):
        return GetEntitySetFilter.format_filter(self._proprty, 'lt', value)

    def __le__(self, value):
        return GetEntitySetFilter.format_filter(self._proprty, 'le', value)

    def __ge__(self, value):
        return GetEntitySetFilter.format_filter(self._proprty, 'ge', value)

    def __gt__(self, value):
        return GetEntitySetFilter.format_filter(self._proprty, 'gt', value)


class FilterExpression:
    """A class representing named expression of OData $filter"""

    def __init__(self, **kwargs):
        self._expressions = kwargs
        self._other = None
        self._operator = None

    @property
    def expressions(self):
        """Get expressions where key is property name with the operator suffix
           and value is the left hand side operand.
        """

        return self._expressions.items()

    @property
    def other(self):
        """Get an instance of the other operand"""

        return self._other

    @property
    def operator(self):
        """The other operand"""

        return self._operator

    def __or__(self, other):
        if self._other is not None:
            raise RuntimeError('The FilterExpression already initialized')

        self._other = other
        self._operator = "or"
        return self

    def __and__(self, other):
        if self._other is not None:
            raise RuntimeError('The FilterExpression already initialized')

        self._other = other
        self._operator = "and"
        return self


class GetEntitySetFilterChainable:
    """
    Example expressions
        FirstName='Tim'
        FirstName__contains='Tim'
        Age__gt=56
        Age__gte=6
        Age__lt=78
        Age__lte=90
        Age__range=(5,9)
        FirstName__in=['Tim', 'Bob', 'Sam']
        FirstName__startswith='Tim'
        FirstName__endswith='mothy'
        Addresses__Suburb='Chatswood'
        Addresses__Suburb__contains='wood'
    """

    OPERATORS = [
        'startswith',
        'endswith',
        'lt',
        'lte',
        'gt',
        'gte',
        'contains',
        'range',
        'in',
        'length',
        'eq'
    ]

    def __init__(self, entity_type, filter_expressions, exprs):
        self._entity_type = entity_type
        self._filter_expressions = filter_expressions
        self._expressions = exprs

    @property
    def expressions(self):
        """Get expressions as a list of tuples where the first item
           is a property name with the operator suffix and the second item
           is a left hand side value.
        """

        return self._expressions.items()

    def proprty_obj(self, name):
        """Returns a model property for a particular property"""

        return self._entity_type.proprty(name)

    def _decode_and_combine_filter_expression(self, filter_expression):
        filter_expressions = [self._decode_expression(expr, val) for expr, val in filter_expression.expressions]
        return self._combine_expressions(filter_expressions)

    def _process_query_objects(self):
        """Processes FilterExpression objects to OData lookups"""

        filter_expressions = []

        for expr in self._filter_expressions:
            lhs_expressions = self._decode_and_combine_filter_expression(expr)

            if expr.other is not None:
                rhs_expressions = self._decode_and_combine_filter_expression(expr.other)
                filter_expressions.append(f'({lhs_expressions}) {expr.operator} ({rhs_expressions})')
            else:
                filter_expressions.append(lhs_expressions)

        return filter_expressions

    def _process_expressions(self):
        filter_expressions = [self._decode_expression(expr, val) for expr, val in self.expressions]

        filter_expressions.extend(self._process_query_objects())

        return filter_expressions

    def _decode_expression(self, expr, val):
        field = None
        # field_heirarchy = []
        operator = 'eq'
        exprs = expr.split('__')

        for part in exprs:
            if self._entity_type.has_proprty(part):
                field = part
                # field_heirarchy.append(part)
            elif part in self.__class__.OPERATORS:
                operator = part
            else:
                raise ValueError(f'"{part}" is not a valid property or operator')
        # field = '/'.join(field_heirarchy)

        # target_field = self.proprty_obj(field_heirarchy[-1])
        expression = self._build_expression(field, operator, val)

        return expression

    # pylint: disable=no-self-use
    def _combine_expressions(self, expressions):
        return ' and '.join(expressions)

    # pylint: disable=too-many-return-statements, too-many-branches
    def _build_expression(self, field_name, operator, value):
        target_field = self.proprty_obj(field_name)

        if operator not in ['length', 'in', 'range']:
            value = target_field.to_literal(value)

        if operator == 'lt':
            return f'{field_name} lt {value}'

        if operator == 'lte':
            return f'{field_name} le {value}'

        if operator == 'gte':
            return f'{field_name} ge {value}'

        if operator == 'gt':
            return f'{field_name} gt {value}'

        if operator == 'startswith':
            return f'startswith({field_name}, {value}) eq true'

        if operator == 'endswith':
            return f'endswith({field_name}, {value}) eq true'

        if operator == 'length':
            value = int(value)
            return f'length({field_name}) eq {value}'

        if operator in ['contains']:
            return f'substringof({value}, {field_name}) eq true'

        if operator == 'range':
            if not isinstance(value, (tuple, list)):
                raise TypeError(f'Range must be tuple or list not {type(value)}')

            if len(value) != 2:
                raise ValueError('Only two items can be passed in a range.')

            low_bound = target_field.to_literal(value[0])
            high_bound = target_field.to_literal(value[1])

            return f'{field_name} gte {low_bound} and {field_name} lte {high_bound}'

        if operator == 'in':
            literal_values = (f'{field_name} eq {target_field.to_literal(item)}' for item in value)
            return ' or '.join(literal_values)

        if operator == 'eq':
            return f'{field_name} eq {value}'

        raise ValueError(f'Invalid expression {operator}')

    def __str__(self):
        expressions = self._process_expressions()
        result = self._combine_expressions(expressions)
        return result


class GetEntitySetRequest(QueryRequest):
    """GET on EntitySet"""

    def __init__(self, url, connection, handler, last_segment, entity_type):
        super(GetEntitySetRequest, self).__init__(url, connection, handler, last_segment)

        self._entity_type = entity_type

    def __getattr__(self, name):
        proprty = self._entity_type.proprty(name)
        return GetEntitySetFilter(proprty)

    def _set_filter(self, filter_val):
        filter_text = self._filter + ' and ' if self._filter else ''
        filter_text += filter_val
        self._filter = filter_text

    def filter(self, *args, **kwargs):
        if args and len(args) == 1 and isinstance(args[0], str):
            self._filter = args[0]
        else:
            self._set_filter(str(GetEntitySetFilterChainable(self._entity_type, args, kwargs)))

        return self


class ListWithTotalCount(list):
    """
    A list with the additional property total_count and next_url.

    If set, use next_url to fetch the next batch of entities.
    """

    def __init__(self, total_count, next_url):
        super(ListWithTotalCount, self).__init__()
        self._total_count = total_count
        self._next_url = next_url

    @property
    def next_url(self):
        """
        URL which identifies the next partial set of entities from the originally identified complete set. None if no
        entities remaining.
        """
        return self._next_url

    @property
    def total_count(self):
        """Count of all entities"""
        if self._total_count is None:
            raise ProgramError('The collection does not include Total Count '
                               'of items because the request was made without '
                               'specifying "count(inline=True)".')

        return self._total_count


class EntitySetProxy:
    """EntitySet Proxy"""

    def __init__(self, service, entity_set, alias=None, parent_last_segment=None):
        """Creates new Entity Set object

            @param alias  in case the entity set is access via assossiation
            @param parent_last_segment  in case of association also parent key must be used
        """
        self._service = service
        self._entity_set = entity_set
        self._alias = alias
        if parent_last_segment is None:
            self._parent_last_segment = ''
        else:
            if parent_last_segment.endswith('/'):
                self._parent_last_segment = parent_last_segment
            else:
                self._parent_last_segment = parent_last_segment + '/'
        self._name = entity_set.name
        self._key = entity_set.entity_type.key_proprties
        self._logger = logging.getLogger(LOGGER_NAME)

        self._logger.debug('New entity set proxy instance for %s', self._name)

    @property
    def service(self):
        """Return service"""
        return self._service

    @property
    def last_segment(self):
        """Return last segment of url"""

        entity_set_name = self._alias if self._alias is not None else self._entity_set.name
        return self._parent_last_segment + entity_set_name

    def nav(self, nav_property, key):
        """Navigates to given navigation property and returns the EntitySetProxy"""

        try:
            navigation_property = self._entity_set.entity_type.nav_proprty(nav_property)
        except KeyError:
            raise PyODataException('Navigation property {} is not declared in {} entity type'.format(
                nav_property, self._entity_set.entity_type))

        # Get entity set of navigation property
        association_info = navigation_property.association_info
        association_set = self._service.schema.association_set_by_association(
            association_info.name)

        end = association_set.end_by_role(navigation_property.to_role.role)
        navigation_entity_set = self._service.schema.entity_set(end.entity_set_name)

        if navigation_property.to_role.multiplicity != model.EndRole.MULTIPLICITY_ZERO_OR_MORE:
            return self._get_nav_entity(key, nav_property, navigation_entity_set)

        return EntitySetProxy(
            self._service,
            navigation_entity_set,
            nav_property,
            self._entity_set.name + key.to_key_string())

    def _get_nav_entity(self, master_key, nav_property, navigation_entity_set):
        """Get entity based on provided key of the master and Navigation property name"""

        def get_entity_handler(parent, nav_property, navigation_entity_set, response):
            """Gets entity from HTTP response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Entity {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity = response.json()['d']

            return NavEntityProxy(parent, nav_property, navigation_entity_set.entity_type, entity)

        self._logger.info(
            'Getting the nav property %s of the entity %s for the key %s',
            nav_property,
            self._entity_set.entity_type.name,
            master_key)

        parent = EntityProxy(self._service, self, self._entity_set.entity_type, entity_key=master_key)

        return NavEntityGetRequest(
            partial(get_entity_handler, parent, nav_property, navigation_entity_set),
            master_key,
            self,
            nav_property)

    def get_entity(self, key=None, **args):
        """Get entity based on provided key properties"""

        def get_entity_handler(response):
            """Gets entity from HTTP response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Entity {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity = response.json()['d']
            etag = response.headers.get('ETag', None)

            return EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, entity, etag=etag)

        if key is not None and isinstance(key, EntityKey):
            entity_key = key
        else:
            entity_key = EntityKey(self._entity_set.entity_type, key, **args)

        self._logger.info('Getting entity %s for key %s and args %s', self._entity_set.entity_type.name, key, args)

        return EntityGetRequest(get_entity_handler, entity_key, self)

    def get_entities(self):
        """Get some, potentially all entities"""

        def get_entities_handler(response):
            """Gets entity set from HTTP Response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Entity Set {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            content = response.json()

            if isinstance(content, int):
                return content

            entities = content['d']
            total_count = None
            next_url = None

            if isinstance(entities, dict):
                if '__count' in entities:
                    total_count = int(entities['__count'])
                if '__next' in entities:
                    next_url = entities['__next']
                entities = entities['results']

            self._logger.info('Fetched %d entities', len(entities))

            result = ListWithTotalCount(total_count, next_url)
            for props in entities:
                entity = EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, props)
                result.append(entity)

            return result

        entity_set_name = self._alias if self._alias is not None else self._entity_set.name
        return GetEntitySetRequest(self._service.url, self._service.connection, get_entities_handler,
                                   self._parent_last_segment + entity_set_name, self._entity_set.entity_type)

    def create_entity(self, return_code=HTTP_CODE_CREATED):
        """Creates a new entity in the given entity-set."""

        def create_entity_handler(response):
            """Gets newly created entity encoded in HTTP Response"""

            if response.status_code != return_code:
                raise HttpError('HTTP POST for Entity Set {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity_props = response.json()['d']
            etag = response.headers.get('ETag', None)

            return EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, entity_props, etag=etag)

        return EntityCreateRequest(self._service.url, self._service.connection, create_entity_handler, self._entity_set,
                                   self.last_segment)

    def update_entity(self, key=None, method=None, **kwargs):
        """Updates an existing entity in the given entity-set."""

        def update_entity_handler(response):
            """Gets modified entity encoded in HTTP Response"""

            if response.status_code != 204:
                raise HttpError('HTTP modify request for Entity Set {} failed with status code {}'
                                .format(self._name, response.status_code), response)

        if key is not None and isinstance(key, EntityKey):
            entity_key = key
        else:
            entity_key = EntityKey(self._entity_set.entity_type, key, **kwargs)

        self._logger.info('Updating entity %s for key %s and args %s', self._entity_set.entity_type.name, key, kwargs)

        if method is None:
            method = self._service.config['http']['update_method']

        return EntityModifyRequest(self._service.url, self._service.connection, update_entity_handler, self._entity_set,
                                   entity_key, method=method)

    def delete_entity(self, key: EntityKey = None, **kwargs):
        """Delete the entity"""

        def delete_entity_handler(response):
            """Check if entity deletion was successful"""

            if response.status_code != 204:
                raise HttpError(f'HTTP POST for Entity delete {self._name} '
                                f'failed with status code {response.status_code}',
                                response)

        if key is not None and isinstance(key, EntityKey):
            entity_key = key
        else:
            entity_key = EntityKey(self._entity_set.entity_type, key, **kwargs)

        return EntityDeleteRequest(self._service.url, self._service.connection, delete_entity_handler, self._entity_set,
                                   entity_key)


# pylint: disable=too-few-public-methods
class EntityContainer:
    """Set of EntitSet proxies"""

    def __init__(self, service):
        self._service = service

        self._entity_sets = dict()

        for entity_set in self._service.schema.entity_sets:
            self._entity_sets[entity_set.name] = EntitySetProxy(self._service, entity_set)

    def __getattr__(self, name):
        try:
            return self._entity_sets[name]
        except KeyError:
            raise AttributeError(
                f"EntitySet {name} not defined in {','.join(list(self._entity_sets.keys()))}.")


class FunctionContainer:
    """Set of Function proxies

       Call a server-side functions (also known as a service operation).
    """

    def __init__(self, service):
        self._service = service

        self._functions = dict()

        for fimport in self._service.schema.function_imports:
            self._functions[fimport.name] = fimport

    def __getattr__(self, name):

        if name not in self._functions:
            raise AttributeError(
                f"Function {name} not defined in {','.join(list(self._functions.keys()))}.")

        fimport = self._service.schema.function_import(name)

        def function_import_handler(fimport, response):
            """Get function call response from HTTP Response"""

            if 300 <= response.status_code < 400:
                raise HttpError(f'Function Import {fimport.name} requires Redirection which is not supported',
                                response)

            if response.status_code == 401:
                raise HttpError(f'Not authorized to call Function Import {fimport.name}',
                                response)

            if response.status_code == 403:
                raise HttpError(f'Missing privileges to call Function Import {fimport.name}',
                                response)

            if response.status_code == 405:
                raise HttpError(
                    f'Despite definition Function Import {fimport.name} does not support HTTP {fimport.http_method}',
                    response)

            if 400 <= response.status_code < 500:
                raise HttpError(
                    f'Function Import {fimport.name} call has failed with status code {response.status_code}',
                    response)

            if response.status_code >= 500:
                raise HttpError(f'Server has encountered an error while processing Function Import {fimport.name}',
                                response)

            if fimport.return_type is None:
                if response.status_code != 204:
                    logging.getLogger(LOGGER_NAME).warning(
                        'The No Return Function Import %s has replied with HTTP Status Code %d instead of 204',
                        fimport.name, response.status_code)

                if response.text:
                    logging.getLogger(LOGGER_NAME).warning(
                        'The No Return Function Import %s has returned content:\n%s', fimport.name, response.text)

                return None

            if response.status_code != 200:
                logging.getLogger(LOGGER_NAME).warning(
                    'The Function Import %s has replied with HTTP Status Code %d instead of 200',
                    fimport.name, response.status_code)

            response_data = response.json()['d']

            # 1. if return types is "entity type", return instance of appropriate entity proxy
            if isinstance(fimport.return_type, model.EntityType):
                entity_set = self._service.schema.entity_set(fimport.entity_set_name)
                return EntityProxy(self._service, entity_set, fimport.return_type, response_data)

            # 2. return raw data for all other return types (primitives, complex types encoded in dicts, etc.)
            return response_data

        return FunctionRequest(self._service.url, self._service.connection,
                               partial(function_import_handler, fimport), fimport)


class Service:
    """OData service"""

    def __init__(self, url, schema, connection, config=None):
        self._url = url
        self._schema = schema
        self._connection = connection
        self._retain_null = config.retain_null if config else False
        self._entity_container = EntityContainer(self)
        self._function_container = FunctionContainer(self)

        self._config = {'http': {'update_method': 'PATCH'}}

    @property
    def schema(self):
        """Parsed metadata"""

        return self._schema

    @property
    def url(self):
        """Service url"""

        return self._url

    @property
    def connection(self):
        """Service connection"""

        return self._connection

    @property
    def retain_null(self):
        """Whether to respect null-ed values or to substitute them with type specific default values"""

        return self._retain_null

    @property
    def entity_sets(self):
        """EntitySet proxy"""

        return self._entity_container

    @property
    def functions(self):
        """Functions proxy"""

        return self._function_container

    @property
    def config(self):
        """Service specific configuration"""

        return self._config

    def http_get(self, path, connection=None):
        """HTTP GET response for the passed path in the service"""

        conn = connection
        if conn is None:
            conn = self._connection

        return conn.get(urljoin(self._url, path))

    async def async_http_get(self, path, connection=None):
        """HTTP GET response for the passed path in the service"""

        conn = connection
        if conn is None:
            conn = self._connection

        async with conn.get(urljoin(self._url, path)) as resp:
            return resp

    def http_get_odata(self, path, handler, connection=None):
        """HTTP GET request proxy for the passed path in the service"""

        conn = connection
        if conn is None:
            conn = self._connection

        return ODataHttpRequest(
            urljoin(self._url, path),
            conn,
            handler,
            headers={'Accept': 'application/json'})

    def create_batch(self, batch_id=None):
        """Create instance of OData batch request"""

        def batch_handler(batch, parts):
            """Process parsed multipart request (parts)"""

            logging.getLogger(LOGGER_NAME).debug('Batch handler called for batch %s', batch.id)

            result = []
            for part, req in zip(parts, batch.requests):
                logging.getLogger(LOGGER_NAME).debug('Batch handler is processing part %s for request %s', part, req)

                # if part represents multiple requests, dont' parse body and
                # process parts by appropriate reuqest instance
                if isinstance(req, MultipartRequest):
                    result.append(req.handler(req, part))
                else:
                    # part represents single request, we have to parse
                    # content (without checking Content type for binary/http)
                    response = ODataHttpResponse.from_string(part[0])
                    result.append(req.handler(response))
            return result

        return BatchRequest(self._url, self._connection, batch_handler, batch_id)

    def create_changeset(self, changeset_id=None):
        """Create instance of OData changeset"""

        def changeset_handler(changeset, parts):
            """Gets changeset response from HTTP response"""

            logging.getLogger(LOGGER_NAME).debug('Changeset handler called for changeset %s', changeset.id)

            result = []

            # check if changeset response consists of parts, this is important
            # to distinguish cases when server responds with single HTTP response
            # for whole request
            if not isinstance(parts[0], list):
                # raise error (even for successfull status codes) since such changeset response
                # always means something wrong happened on server
                response = ODataHttpResponse.from_string(parts[0])
                raise HttpError('Changeset cannot be processed due to single response received, status code: {}'.format(
                    response.status_code), response)

            for part, req in zip(parts, changeset.requests):
                logging.getLogger(LOGGER_NAME).debug('Changeset handler is processing part %s for request %s', part,
                                                     req)

                if isinstance(req, MultipartRequest):
                    raise PyODataException('Changeset cannot contain nested multipart content')

                # part represents single request, we have to parse
                # content (without checking Content type for binary/http)
                response = ODataHttpResponse.from_string(part[0])

                result.append(req.handler(response))

            return result

        return Changeset(self._url, self._connection, changeset_handler, changeset_id)


class MultipartRequest(ODataHttpRequest):
    """HTTP Batch request"""

    def __init__(self, url, connection, handler, request_id=None):
        super(MultipartRequest, self).__init__(url, connection, partial(MultipartRequest.http_response_handler, self))

        self.requests = []
        self._handler_decoded = handler

        # generate random id of form dddd-dddd-dddd
        # pylint: disable=invalid-name
        self.id = request_id if request_id is not None else '{}_{}_{}'.format(
            random.randint(1000, 9999), random.randint(1000, 9999), random.randint(1000, 9999))

        self._logger.debug('New multipart %s request initialized, id=%s', self.__class__.__name__, self.id)

    @property
    def handler(self):
        return self._handler_decoded

    def get_boundary(self):
        """Get boundary used for request parts"""
        return self.id

    def get_default_headers(self):
        # pylint: disable=no-self-use
        return {'Content-Type': f'multipart/mixed;boundary={self.get_boundary()}'}

    def get_body(self):
        return encode_multipart(self.get_boundary(), self.requests)

    def add_request(self, request):
        """Add request to be sent in batch"""

        self.requests.append(request)
        self._logger.debug('New %s request added to multipart request %s', request.get_method(), self.id)

    @staticmethod
    def http_response_handler(request, response):
        """Process HTTP response to mutipart HTTP request"""

        if response.status_code != 202:  # 202 Accepted
            raise HttpError('HTTP POST for multipart request {0} failed with status code {1}'
                            .format(request.id, response.status_code), response)

        logging.getLogger(LOGGER_NAME).debug('Generic multipart http response request handler called')

        # get list of all parts (headers + body)
        decoded = decode_multipart(response.content.decode('utf-8'), response.headers['Content-Type'])

        return request.handler(request, decoded)


class BatchRequest(MultipartRequest):
    """HTTP Batch request"""

    def get_boundary(self):
        return 'batch_' + self.id

    def get_path(self):
        # pylint: disable=no-self-use
        return '$batch'

    def get_method(self):
        # pylint: disable=no-self-use
        return 'POST'


class Changeset(MultipartRequest):
    """Representation of changeset (unsorted group of requests)"""

    def get_boundary(self):
        return 'changeset_' + self.id
