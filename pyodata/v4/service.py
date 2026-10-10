"""OData V4 service implementation

   IDENTICAL classes are imported directly from v2.service.
   V4-specific classes are written fresh.
"""

# pylint: disable=too-many-lines

import logging
from functools import partial
import json
import random
from urllib.parse import urlencode, quote, urlparse

from pyodata.exceptions import HttpError, PyODataException
from pyodata.v4 import model

# Classes with zero V2/V4 differences — imported directly from v2.
# pylint: disable=unused-import
from pyodata.v2.service import (
    urljoin,
    decode_multipart,
    ODataHttpResponse,
    GetEntitySetFilter,
    FilterExpression,          # re-exported as part of the public V4 service API
    ListWithTotalCount,
    # Pure filter-expression builder — no wire-format logic, reused as-is.
    GetEntitySetFilterChainable,
)
# pylint: enable=unused-import

# NOTE: EntityContainer is NOT imported from v2 even though its body is textually
# identical: v2.service.EntityContainer closes over v2.service.EntitySetProxy (resolved
# at v2 module scope), so importing it would build V2 proxies with V2 wire-format logic.
# It is therefore written fresh below so it instantiates the V4 EntitySetProxy.

LOGGER_NAME = 'pyodata.v4.service'

HTTP_CODE_OK = 200
HTTP_CODE_CREATED = 201
HTTP_CODE_NO_CONTENT = 204


def encode_multipart(boundary, http_requests):
    """Encode list of requests into multipart body (V4: adds OData-Version in part headers)"""

    lines = []

    lines.append('')

    for req in http_requests:

        lines.append(f'--{boundary}')

        if not isinstance(req, MultipartRequest):
            lines.extend(('Content-Type: application/http', 'Content-Transfer-Encoding:binary'))

            lines.append('')

            # request  line (method + path + query params)
            line = f'{req.get_method()} {req.get_path()}'
            query_params = urlencode(req.get_query_params())
            if query_params:
                line += '?' + query_params
            line += ' HTTP/1.1'

            lines.append(line)

            # V4 requires the OData-Version header on each inner request part.
            lines.append('OData-Version: 4.0')

        # request specific headers
        for hdr, hdr_val in req.get_headers().items():
            lines.append(f'{hdr}: {hdr_val}')

        lines.append('')

        body = req.get_body()
        if body is not None:
            lines.append(req.get_body())
        else:
            lines.append('')

    lines.append(f'--{boundary}--')

    return '\r\n'.join(lines)


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

    def __init__(self, url, connection, handler, headers=None, response_hook=None):
        self._connection = connection
        self._url = url
        self._handler = handler
        self._headers = headers or dict()
        self._logger = logging.getLogger(LOGGER_NAME)
        self._customs = {}  # string -> string hash
        self._next_url = None
        self._response_hook = response_hook

    @property
    def handler(self):
        """Getter for handler"""
        return self._handler

    def get_path(self):
        """Get path of the HTTP request"""
        return ''

    def get_query_params(self):
        """Get query params"""
        return dict(self._customs)

    def get_method(self):
        """Get HTTP method"""
        return 'GET'

    def get_body(self):
        """Get HTTP body or None if not applicable"""
        return None

    def get_default_headers(self):
        """Get dict of Child specific HTTP headers"""
        return {'OData-Version': '4.0'}

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
            parsed_next = urlparse(self._next_url)
            parsed_base = urlparse(self._url)
            if (parsed_next.scheme, parsed_next.netloc) != (parsed_base.scheme, parsed_base.netloc):
                raise PyODataException(
                    f'cross-origin nextLink URL rejected: {self._next_url!r} differs from '
                    f'service root {self._url!r}'
                )
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
        """Fetches HTTP response and returns processed result"""

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
        """Fetches HTTP response and returns processed result"""

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

        if self._response_hook is not None:
            self._response_hook(response)

        return self._handler(response)

    def custom(self, name, value):
        """Adds a custom name-value pair."""
        # returns QueryRequest
        self._customs[name] = value
        return self


class EntityGetRequest(ODataHttpRequest):
    """Used for GET operations of a single entity"""

    def __init__(self, handler, entity_key, entity_set_proxy, encode_path=True):
        super().__init__(entity_set_proxy.service.url, entity_set_proxy.service.connection,
                         handler, response_hook=entity_set_proxy.service.response_hook)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._entity_key = entity_key
        self._entity_set_proxy = entity_set_proxy
        self._select = None
        self._expand = None
        self._encode_path = encode_path

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
        if isinstance(expand, dict):
            raise NotImplementedError(
                'V4 nested $expand options (dict) are not yet implemented; pass a string expression')
        self._expand = expand
        return self

    def get_path(self):
        if self.get_encode_path():
            return quote(self._entity_set_proxy.last_segment + self._entity_key.to_key_string())
        return self._entity_set_proxy.last_segment + self._entity_key.to_key_string()

    def get_default_headers(self):
        headers = super().get_default_headers()
        headers['Accept'] = 'application/json'
        return headers

    def get_query_params(self):
        qparams = super().get_query_params()

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

    def get_encode_path(self):
        """Getter for encode path flag"""
        return self._encode_path


class NavEntityGetRequest(EntityGetRequest):
    """Used for GET operations of a single entity accessed via a Navigation property"""

    def __init__(self, handler, master_key, entity_set_proxy, nav_property):
        super().__init__(handler, master_key, entity_set_proxy)

        self._nav_property = nav_property

    def get_path(self):
        return f"{super().get_path()}/{self._nav_property}"


class EntityCreateRequest(ODataHttpRequest):
    """Used for creating entities (POST operations of a single entity)

       Call execute() to send the create-request to the OData service
       and get the newly created entity."""

    def __init__(self, url, connection, handler, entity_set, last_segment=None, response_hook=None):
        super().__init__(url, connection, handler, response_hook=response_hook)
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
        return {'Accept': 'application/json', 'Content-Type': 'application/json'}

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

        self._values = EntityCreateRequest._build_values(self._entity_type, kwargs)

        return self


class EntityDeleteRequest(ODataHttpRequest):
    """Used for deleting entity (DELETE operations on a single entity)"""

    def __init__(self, url, connection, handler, entity_set, entity_key, encode_path=True, response_hook=None):
        super().__init__(url, connection, handler, response_hook=response_hook)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._entity_set = entity_set
        self._entity_key = entity_key
        self._encode_path = encode_path

        self._logger.debug('New instance of EntityDeleteRequest for entity type: %s', entity_set.entity_type.name)

    def get_path(self):
        if self.get_encode_path():
            return quote(self._entity_set.name + self._entity_key.to_key_string())
        return self._entity_set.name + self._entity_key.to_key_string()

    def get_encode_path(self):
        """Getter for encode path flag"""
        return self._encode_path

    def get_method(self):
        return 'DELETE'


# pylint: disable=too-many-instance-attributes
class EntityModifyRequest(ODataHttpRequest):
    """Used for modyfing entities (PATCH/PUT operations on a single entity)

       Call execute() to send the update-request to the OData service
       and get the modified entity."""

    ALLOWED_HTTP_METHODS = ['PATCH', 'PUT']

    # pylint: disable=too-many-arguments
    def __init__(self, url, connection, handler, entity_set, entity_key, method="PATCH", encode_path=True,
                 response_hook=None):
        super().__init__(url, connection, handler, response_hook=response_hook)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._entity_set = entity_set
        self._entity_type = entity_set.entity_type
        self._entity_key = entity_key
        self._encode_path = encode_path

        self._method = method.upper()
        if self._method not in EntityModifyRequest.ALLOWED_HTTP_METHODS:
            raise ValueError('The value "{}" is not on the list of allowed Entity Update HTTP Methods: {}'
                             .format(method, ', '.join(EntityModifyRequest.ALLOWED_HTTP_METHODS)))

        self._values = {}

        # get all properties declared by entity type
        self._type_props = self._entity_type.proprties()

        self._logger.debug('New instance of EntityModifyRequest for entity type: %s', self._entity_type.name)

    def get_path(self):
        if self.get_encode_path():
            return quote(self._entity_set.name + self._entity_key.to_key_string())
        return self._entity_set.name + self._entity_key.to_key_string()

    def get_method(self):
        return self._method

    def get_body(self):
        body = {}
        for key, val in self._values.items():
            body[key] = val
        return json.dumps(body)

    def get_default_headers(self):
        return {'Accept': 'application/json', 'Content-Type': 'application/json'}

    def get_encode_path(self):
        """Getter for encode path flag"""
        return self._encode_path

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

    def __init__(self, url, connection, handler, last_segment, response_hook=None):
        super().__init__(url, connection, handler, response_hook=response_hook)

        self._logger = logging.getLogger(LOGGER_NAME)
        self._count = None
        self._inlinecount = None
        self._top = None
        self._skip = None
        self._order_by = None
        self._filter = None
        self._select = None
        self._expand = None
        self._search = None
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
        """
        self._next_url = next_url
        return self

    def expand(self, expand):
        """Sets the expand expressions."""
        if isinstance(expand, dict):
            raise NotImplementedError(
                'V4 nested $expand options (dict) are not yet implemented; pass a string expression')
        self._expand = expand
        return self

    def filter(self, filter_val):
        """Sets the filter expression."""
        # returns QueryRequest
        self._filter = filter_val
        return self

    def order_by(self, order_by):
        """Sets the ordering expressions."""
        self._order_by = order_by
        return self

    def select(self, select):
        """Sets the selection clauses."""
        self._select = select
        return self

    def search(self, text):
        """Sets the $search expression (V4 free-text search)."""
        self._search = text
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
            return {'OData-Version': '4.0'}

        return {
            'Accept': 'application/json',
            'OData-Version': '4.0',
        }

    def get_query_params(self):
        if self._next_url:
            return {}

        qparams = super().get_query_params()

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

        if self._search is not None:
            qparams['$search'] = self._search

        if self._inlinecount:
            qparams['$count'] = 'true'

        return qparams


class GetEntitySetRequest(QueryRequest):
    """GET on EntitySet"""

    def __init__(self, url, connection, handler, last_segment, entity_type, encode_path=True, response_hook=None):
        super().__init__(url, connection, handler, last_segment, response_hook=response_hook)

        self._entity_type = entity_type
        self._encode_path = encode_path

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

    def get_path(self):
        if self.get_encode_path():
            path = quote(self._last_segment)
        else:
            path = self._last_segment

        if self._count:
            return urljoin(path, '/$count')
        return path

    def get_encode_path(self):
        """Getter for encode path flag"""
        return self._encode_path


class FunctionRequest(ODataHttpRequest):
    """V4 Function import request (unbound function invocation).

       V4 unbound functions are invoked via a GET with parameters embedded in
       the resource path: ``FunctionName(param=value,...)``.
    """

    def __init__(self, url, connection, handler, function_import, response_hook=None):
        super().__init__(url, connection, handler, response_hook=response_hook)

        self._logger = logging.getLogger(LOGGER_NAME)
        self._function_import = function_import
        self._params = {}

        self._logger.debug('New instance of FunctionRequest for %s', self._function_import.name)

    def parameter(self, name, value):
        """Sets value of parameter."""

        # check if param is valid (is declared in metadata)
        try:
            param = self._function_import.function.get_parameter(name)
        except (KeyError, AttributeError):
            raise PyODataException('Function import {0} does not have parameter {1}'
                                   .format(self._function_import.name, name))

        # V4 function parameters are serialized as URL literals in the path.
        self._params[param.name] = param.to_literal(value)

        return self

    def get_path(self):
        params = ','.join(f'{name}={value}' for name, value in self._params.items())
        return f'{self._function_import.name}({params})'

    def get_query_params(self):
        # V4 function params go in the path, not the query string.
        return {}

    def get_method(self):
        return 'GET'

    def get_default_headers(self):
        return {'Accept': 'application/json', 'OData-Version': '4.0'}


class ActionRequest(ODataHttpRequest):
    """V4 Action invocation — always POST, parameters as JSON body."""

    def __init__(self, url, connection, handler, action_import, response_hook=None):
        super().__init__(url, connection, handler, response_hook=response_hook)

        self._logger = logging.getLogger(LOGGER_NAME)
        self._action_import = action_import
        self._action = action_import.action
        self._params = {}
        self._entity_key = None

        self._logger.debug('New instance of ActionRequest for %s', self._action_import.name)

    def with_entity(self, entity_key):
        """Binds this action to a resource path segment (for bound actions)."""
        self._entity_key = entity_key
        return self

    def get_method(self):
        return 'POST'

    def get_path(self):
        if self._entity_key is not None:
            namespace = getattr(self._action, 'namespace', None)
            qualified = f'{namespace}.{self._action.name}' if namespace else self._action.name
            return f'{self._entity_key}/{qualified}'
        return self._action_import.name

    def get_body(self):
        return json.dumps(self._params)

    def get_default_headers(self):
        return {'Content-Type': 'application/json', 'Accept': 'application/json',
                'OData-Version': '4.0'}

    def parameter(self, name, value):
        """Sets value of parameter (validated against the action's parameters)."""
        try:
            param = self._action.get_parameter(name)
        except (KeyError, AttributeError):
            raise PyODataException('Action import {0} does not have parameter {1}'
                                   .format(self._action_import.name, name))

        self._params[param.name] = param.to_json(value)
        return self


# pylint: disable=too-many-instance-attributes
class EntityProxy:
    """An immutable OData V4 entity instance, consisting of an identity (an
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
        self._odata_id = None
        self._odata_context = None

        self._logger.debug('New entity proxy instance of type %s from properties: %s', entity_type.name, proprties)

        # cache values of individual properties if provided
        if proprties is not None:

            # V4 control information lives in @odata.* annotations on the object itself.
            etag_body = proprties.get('@odata.etag', None)
            if etag is not None and etag_body is not None and etag_body != etag:
                raise PyODataException('Etag from header does not match the Etag from response body')

            if etag_body is not None:
                self._etag = etag_body

            self._odata_id = proprties.get('@odata.id', None)
            self._odata_context = proprties.get('@odata.context', None)

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

                if prop.name not in proprties:
                    continue

                prop_etype = prop.typ
                prop_value = proprties[prop.name]

                if prop.type_info.is_collection:
                    # For a collection nav, prop.typ is a Collection; use its item type.
                    item_etype = prop_etype.item_type if isinstance(prop_etype, model.Collection) else prop_etype
                    self._cache[prop.name] = []
                    if isinstance(prop_value, dict) and 'value' in prop_value:
                        items = prop_value['value']
                    elif isinstance(prop_value, list):
                        items = prop_value
                    else:
                        items = []
                    for entity in items:
                        self._cache[prop.name].append(EntityProxy(service, None, item_etype, entity))
                else:
                    if prop_value is None:
                        self._cache[prop.name] = None
                    else:
                        self._cache[prop.name] = EntityProxy(service, None, prop_etype, prop_value)

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
        """Navigates to given navigation property and returns the EntitySetProxy or entity"""

        try:
            navigation_property = self._entity_type.nav_proprty(nav_property)
        except KeyError:
            raise PyODataException('Navigation property {} is not declared in {} entity type'.format(
                nav_property, self._entity_type))

        # V4: target entity type is referenced directly, no AssociationSet lookup.
        target_entity_type = navigation_property.typ

        if navigation_property.contains_target or navigation_property.type_info.is_collection:
            # A contained target is addressed relative to the parent and need not
            # have a backing EntitySet, so resolve one only when it exists.
            target_entity_set = None
            if not navigation_property.contains_target:
                target_entity_set = self._service.schema.entity_set_for_type(target_entity_type.name)
            return EntitySetProxy(
                self._service,
                target_entity_set,
                nav_property,
                self._entity_set.name + self._entity_key.to_key_string())

        target_entity_set = self._service.schema.entity_set_for_type(target_entity_type.name)
        return self._get_nav_entity(nav_property, target_entity_set)

    def _get_nav_entity(self, nav_property, navigation_entity_set):
        """Get entity based on Navigation property name"""

        def get_entity_handler(parent, nav_property, navigation_entity_set, response):
            """Gets entity from HTTP response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Entity {0} failed with status code {1}'
                                .format(nav_property, response.status_code), response)

            entity = response.json()

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

            data = response.json()
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

    @property
    def odata_id(self):
        """V4 @odata.id control information for this entity"""
        return self._odata_id

    @property
    def odata_context(self):
        """V4 @odata.context control information for this entity"""
        return self._odata_context

    def equals(self, other):
        """Returns true if the self and the other contains the same data"""
        # pylint: disable=W0212
        return self._cache == other._cache


class NavEntityProxy(EntityProxy):
    """Special case of an Entity access via 1 to 1 Navigation property"""

    def __init__(self, parent_entity, prop_name, entity_type, entity):
        # pylint: disable=protected-access
        super().__init__(parent_entity._service, parent_entity._entity_set, entity_type, entity)

        self._parent_entity = parent_entity
        self._prop_name = prop_name

    def get_path(self):
        """Returns URL of the entity"""

        return urljoin(self._parent_entity.get_path(), self._prop_name)


class EntitySetProxy:
    """EntitySet Proxy"""

    def __init__(self, service, entity_set, alias=None, parent_last_segment=None):
        """Creates new Entity Set object

            @param alias  in case the entity set is accessed via a navigation property
            @param parent_last_segment  in case of navigation also parent key must be used
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
        # A contained navigation target may have no backing EntitySet; in that
        # case it is addressed relative to the parent via the alias segment.
        if entity_set is not None:
            self._name = entity_set.name
            self._key = entity_set.entity_type.key_proprties
        else:
            self._name = alias
            self._key = None
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
        """Navigates to given navigation property and returns the EntitySetProxy or entity"""

        try:
            navigation_property = self._entity_set.entity_type.nav_proprty(nav_property)
        except KeyError:
            raise PyODataException('Navigation property {} is not declared in {} entity type'.format(
                nav_property, self._entity_set.entity_type))

        # V4: target entity type is referenced directly, no AssociationSet lookup.
        target_entity_type = navigation_property.typ

        if navigation_property.contains_target or navigation_property.type_info.is_collection:
            # A contained target is addressed relative to the parent and need not
            # have a backing EntitySet, so resolve one only when it exists.
            navigation_entity_set = None
            if not navigation_property.contains_target:
                navigation_entity_set = self._service.schema.entity_set_for_type(target_entity_type.name)
            return EntitySetProxy(
                self._service,
                navigation_entity_set,
                nav_property,
                self._entity_set.name + key.to_key_string())

        navigation_entity_set = self._service.schema.entity_set_for_type(target_entity_type.name)
        return self._get_nav_entity(key, nav_property, navigation_entity_set)

    def _get_nav_entity(self, master_key, nav_property, navigation_entity_set):
        """Get entity based on provided key of the master and Navigation property name"""

        def get_entity_handler(parent, nav_property, navigation_entity_set, response):
            """Gets entity from HTTP response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Entity {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity = response.json()

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

    def get_entity(self, key=None, encode_path=True, **args):
        """Get entity based on provided key properties"""

        def get_entity_handler(response):
            """Gets entity from HTTP response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Entity {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity = response.json()
            etag = response.headers.get('ETag', None)

            return EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, entity, etag=etag)

        if key is not None and isinstance(key, EntityKey):
            entity_key = key
        else:
            entity_key = EntityKey(self._entity_set.entity_type, key, **args)

        self._logger.info('Getting entity %s for key %s and args %s', self._entity_set.entity_type.name, key, args)

        return EntityGetRequest(get_entity_handler, entity_key, self, encode_path=encode_path)

    def get_entities(self, encode_path=True):
        """Get some, potentially all entities"""

        def get_entities_handler(response):
            """Gets entity set from HTTP Response"""

            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Entity Set {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            content = response.json()

            # Response of a /$count request is a bare integer.
            if isinstance(content, int):
                return content

            total_count = None
            next_url = None

            if isinstance(content, dict):
                if '@odata.count' in content:
                    total_count = int(content['@odata.count'])
                if '@odata.nextLink' in content:
                    next_url = content['@odata.nextLink']
                entities = content['value']
            else:
                entities = content

            self._logger.info('Fetched %d entities', len(entities))

            result = ListWithTotalCount(total_count, next_url)
            for props in entities:
                entity = EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, props)
                result.append(entity)

            return result

        entity_set_name = self._alias if self._alias is not None else self._entity_set.name
        return GetEntitySetRequest(self._service.url, self._service.connection, get_entities_handler,
                                   self._parent_last_segment + entity_set_name, self._entity_set.entity_type,
                                   encode_path=encode_path, response_hook=self._service.response_hook)

    def create_entity(self, return_code=HTTP_CODE_CREATED):
        """Creates a new entity in the given entity-set."""

        def create_entity_handler(response):
            """Gets newly created entity encoded in HTTP Response"""

            if response.status_code != return_code:
                raise HttpError('HTTP POST for Entity Set {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity_props = response.json()
            etag = response.headers.get('ETag', None)

            return EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, entity_props, etag=etag)

        return EntityCreateRequest(self._service.url, self._service.connection, create_entity_handler, self._entity_set,
                                   self.last_segment, response_hook=self._service.response_hook)

    def update_entity(self, key=None, method=None, encode_path=True, **kwargs):
        """Updates an existing entity in the given entity-set."""

        def update_entity_handler(response):
            """Gets modified entity encoded in HTTP Response"""

            # OData V4 answers a successful update with 204 No Content, but some services
            # reply 200 OK with the modified entity instead.
            if response.status_code not in (HTTP_CODE_OK, HTTP_CODE_NO_CONTENT):
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
                                   entity_key, method=method, encode_path=encode_path,
                                   response_hook=self._service.response_hook)

    def delete_entity(self, key: EntityKey = None, encode_path=True, **kwargs):
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
                                   entity_key, encode_path=encode_path, response_hook=self._service.response_hook)


class SingletonProxy:
    """Proxy for a V4 Singleton — addressed by name only, with no key predicate."""

    def __init__(self, service, singleton):
        self._service = service
        self._singleton = singleton
        self._name = singleton.name
        self._entity_type = singleton.entity_type
        self._logger = logging.getLogger(LOGGER_NAME)

        self._logger.debug('New singleton proxy instance for %s', self._name)

    @property
    def service(self):
        """Return service"""
        return self._service

    @property
    def name(self):
        """Singleton name"""
        return self._name

    def get_entity(self):
        """GET the singleton entity — path is /SingletonName (no parentheses, no key)."""

        def get_entity_handler(response):
            if response.status_code != HTTP_CODE_OK:
                raise HttpError('HTTP GET for Singleton {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity = response.json()
            etag = response.headers.get('ETag', None)

            return EntityProxy(self._service, None, self._entity_type, entity, etag=etag)

        return ODataHttpRequest(
            urljoin(self._service.url, self._name),
            self._service.connection,
            get_entity_handler,
            headers={'Accept': 'application/json', 'OData-Version': '4.0'},
            response_hook=self._service.response_hook)

    def update_entity(self, method=None, **kwargs):
        """PATCH the singleton entity — path is /SingletonName (no key)."""

        def update_entity_handler(response):
            if response.status_code not in (HTTP_CODE_OK, HTTP_CODE_NO_CONTENT):
                raise HttpError('HTTP modify request for Singleton {} failed with status code {}'
                                .format(self._name, response.status_code), response)

        if method is None:
            method = self._service.config['http']['update_method']

        return _SingletonModifyRequest(self._service.url, self._service.connection, update_entity_handler,
                                       self._singleton, self._entity_type, method=method,
                                       values=kwargs, response_hook=self._service.response_hook)


class _SingletonModifyRequest(ODataHttpRequest):
    """PATCH/PUT request for a V4 Singleton (keyless path)."""

    ALLOWED_HTTP_METHODS = ['PATCH', 'PUT']

    # pylint: disable=too-many-arguments
    def __init__(self, url, connection, handler, singleton, entity_type, method='PATCH', values=None,
                 response_hook=None):
        super().__init__(url, connection, handler, response_hook=response_hook)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._singleton = singleton
        self._entity_type = entity_type

        self._method = method.upper()
        if self._method not in _SingletonModifyRequest.ALLOWED_HTTP_METHODS:
            raise ValueError('The value "{}" is not on the list of allowed Entity Update HTTP Methods: {}'
                             .format(method, ', '.join(_SingletonModifyRequest.ALLOWED_HTTP_METHODS)))

        self._values = {}
        if values:
            self.set(**values)

    def get_path(self):
        return self._singleton.name

    def get_method(self):
        return self._method

    def get_body(self):
        return json.dumps(self._values)

    def get_default_headers(self):
        return {'Accept': 'application/json', 'Content-Type': 'application/json', 'OData-Version': '4.0'}

    def set(self, **kwargs):
        """Set properties to be changed."""
        for key, val in kwargs.items():
            try:
                val = self._entity_type.proprty(key).to_json(val)
            except KeyError:
                raise PyODataException(
                    f'Property {key} is not declared in {self._entity_type.name} entity type')
            self._values[key] = val
        return self


# pylint: disable=too-few-public-methods
class EntityContainer:
    """Set of EntitySet proxies (V4 — builds V4 EntitySetProxy instances)"""

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


class SingletonContainer:
    """Set of Singleton proxies"""

    def __init__(self, service):
        self._service = service

        self._singletons = dict()

        for singleton in self._service.schema.singletons:
            self._singletons[singleton.name] = SingletonProxy(self._service, singleton)

    def __getattr__(self, name):
        try:
            return self._singletons[name]
        except KeyError:
            raise AttributeError(
                f"Singleton {name} not defined in {','.join(list(self._singletons.keys()))}.")


class FunctionContainer:
    """Set of Function and Action proxies.

       Dispatches a call either to a V4 FunctionImport (GET) or an ActionImport (POST).
    """

    def __init__(self, service):
        self._service = service

        self._functions = dict()
        for fimport in self._service.schema.function_imports:
            self._functions[fimport.name] = fimport

        self._actions = dict()
        for aimport in self._service.schema.action_imports:
            self._actions[aimport.name] = aimport

    def _build_response_handler(self, operation):
        """Builds a response handler for a FunctionImport/ActionImport"""

        def _handle_response_status(response):
            if 300 <= response.status_code < 400:
                raise HttpError(f'Operation {operation.name} requires Redirection which is not supported',
                                response)
            if response.status_code == 401:
                raise HttpError(f'Not authorized to call Operation {operation.name}', response)
            if response.status_code == 403:
                raise HttpError(f'Missing privileges to call Operation {operation.name}', response)
            if 400 <= response.status_code < 500:
                raise HttpError(
                    f'Operation {operation.name} call has failed with status code {response.status_code}',
                    response)
            if response.status_code >= 500:
                raise HttpError(f'Server has encountered an error while processing Operation {operation.name}',
                                response)

        def operation_handler(response):
            """Get operation call response from HTTP Response (V4: no 'd' wrapper)"""

            _handle_response_status(response)

            return_type = operation.return_type
            if return_type is None:
                return None

            if response.status_code == HTTP_CODE_NO_CONTENT or not response.content:
                return None

            response_data = response.json()

            match return_type:
                case model.EntityType():
                    entity_set = self._service.schema.entity_set(operation.entity_set_name)
                    return EntityProxy(self._service, entity_set, return_type, response_data)
                case model.Collection():
                    entity_set = self._service.schema.entity_set(operation.entity_set_name)
                    total_count = None
                    next_url = None
                    if '@odata.count' in response_data:
                        total_count = int(response_data['@odata.count'])
                    if '@odata.nextLink' in response_data:
                        next_url = response_data['@odata.nextLink']
                    results = response_data.get('value')
                    if results is None:
                        raise PyODataException(
                            f'Operation {operation.name} returned a Collection response without a "value" key')
                    collection = ListWithTotalCount(total_count, next_url)
                    collection_item_type = return_type.item_type
                    for entity in results:
                        collection.append(EntityProxy(self._service, entity_set, collection_item_type, entity))
                    return collection
                case _:
                    # Scalar / primitive responses are wrapped in {'value': ...} by V4.
                    if isinstance(response_data, dict) and 'value' in response_data:
                        return response_data['value']
                    return response_data

        return operation_handler

    def __getattr__(self, name):
        if name in self._functions:
            fimport = self._service.schema.function_import(name)
            return FunctionRequest(self._service.url, self._service.connection,
                                   self._build_response_handler(fimport), fimport,
                                   response_hook=self._service.response_hook)

        if name in self._actions:
            aimport = self._service.schema.action_import(name)
            return ActionRequest(self._service.url, self._service.connection,
                                 self._build_response_handler(aimport), aimport,
                                 response_hook=self._service.response_hook)

        raise AttributeError(
            "Function/Action {} not defined in {}.".format(
                name, ','.join(list(self._functions.keys()) + list(self._actions.keys()))))


class Service:
    """OData V4 service"""

    def __init__(self, url, schema, connection, config=None, response_hook=None):
        self._url = url
        self._schema = schema
        self._connection = connection
        self._retain_null = config.retain_null if config else False
        self._response_hook = response_hook
        self._entity_container = EntityContainer(self)
        self._function_container = FunctionContainer(self)
        self._singleton_container = SingletonContainer(self)

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
    def response_hook(self):
        """Optional hook called with the raw response before domain handler runs"""

        return self._response_hook

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
        """Functions (and Actions) proxy"""

        return self._function_container

    @property
    def singletons(self):
        """Singleton proxy"""

        return self._singleton_container

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
            headers={'Accept': 'application/json', 'OData-Version': '4.0'})

    def entity_reference(self, *args, **kwargs):
        """V4 /$ref entity reference operations — not yet implemented."""
        raise NotImplementedError('V4 /$ref entity reference operations are not yet implemented')

    def follow_delta_link(self, *args, **kwargs):
        """Following a V4 @odata.deltaLink is not yet implemented.

           Reading @odata.deltaLink from a response is allowed; actively
           following it to fetch a delta payload is deferred.
        """
        raise NotImplementedError('Following V4 @odata.deltaLink (delta link consumption) is not yet implemented')

    def create_json_batch(self, *args, **kwargs):
        """V4 JSON batch format (application/json) — not yet implemented.

           The multipart batch format is supported via create_batch()/create_changeset().
        """
        raise NotImplementedError(
            'V4 JSON batch format (application/json) is not yet implemented; '
            'use create_batch()/create_changeset() for the multipart batch format')

    def create_batch(self, batch_id=None):
        """Create instance of OData multipart batch request"""

        def batch_handler(batch, parts):
            """Process parsed multipart request (parts)"""

            logging.getLogger(LOGGER_NAME).debug('Batch handler called for batch %s', batch.id)

            result = []
            for part, req in zip(parts, batch.requests):
                logging.getLogger(LOGGER_NAME).debug('Batch handler is processing part %s for request %s', part, req)

                if isinstance(req, MultipartRequest):
                    result.append(req.handler(req, part))
                else:
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

            if not isinstance(parts[0], list):
                response = ODataHttpResponse.from_string(parts[0])
                raise HttpError('Changeset cannot be processed due to single response received, status code: {}'.format(
                    response.status_code), response)

            for part, req in zip(parts, changeset.requests):
                logging.getLogger(LOGGER_NAME).debug('Changeset handler is processing part %s for request %s', part,
                                                     req)

                if isinstance(req, MultipartRequest):
                    raise PyODataException('Changeset cannot contain nested multipart content')

                response = ODataHttpResponse.from_string(part[0])

                result.append(req.handler(response))

            return result

        return Changeset(self._url, self._connection, changeset_handler, changeset_id)


class MultipartRequest(ODataHttpRequest):
    """HTTP Batch request"""

    def __init__(self, url, connection, handler, request_id=None):
        super().__init__(url, connection, partial(MultipartRequest.http_response_handler, self))

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
        return {
            'Content-Type': f'multipart/mixed;boundary={self.get_boundary()}',
            'OData-Version': '4.0',
        }

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
        return '$batch'

    def get_method(self):
        return 'POST'


class Changeset(MultipartRequest):
    """Representation of changeset (unsorted group of requests)"""

    def get_boundary(self):
        return 'changeset_' + self.id
