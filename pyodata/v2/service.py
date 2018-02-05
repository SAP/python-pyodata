"""OData service implementation"""

import logging
from functools import partial
import json
import requests
import pyodata
from pyodata.exceptions import HttpError, PyODataException

LOGGER_NAME = 'pyodata.service'


class EntityKey(object):
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
                raise PyODataException(
                    ('Key of entity type {} consists of multiple properties {} '
                     'and cannot be initialized by single value').format(
                         self._entity_type.name,
                         ', '.join([prop.name for prop in self._key])))

            # get single key property and format key string
            key_prop = self._key[0]
            args[key_prop.name] = single_key

            self._type = EntityKey.TYPE_SINGLE

            self._logger.debug(('Detected single property key, adding pair %s->%s to key'
                                'properties'), key_prop.name, single_key)
        else:
            for key_prop in self._key:
                if key_prop.name not in args:
                    raise PyODataException(
                        'Missing value for key property {}'.format(key_prop.name))

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
            return key_prop.typ.traits.to_odata(self._proprties[key_prop.name])

        key_pairs = []
        for key_prop in self._key:

            # if key_prop.name not in self.__dict__['_cache']:
            #    raise RuntimeError('Entity key is not complete, missing value of property: {0}'.format(key_prop.name))

            key_pairs.append('{0}={1}'.format(
                key_prop.name,
                key_prop.typ.traits.to_odata(self._proprties[key_prop.name])))

        return ','.join(key_pairs)

    def to_key_string(self):
        """Gets the string representation of the key, including parentheses"""

        return '({})'.format(self.to_key_string_without_parentheses())

    def __repr__(self):
        return self.to_key_string()


class ODataHttpRequest(object):
    """Deferred HTTP Request"""

    def __init__(self, url, connection, handler, headers=None):
        self._conn = connection
        self._url = url
        self._handler = handler
        self._headers = headers
        self._logger = logging.getLogger(LOGGER_NAME)

    def _get_path(self):
        # pylint: disable=no-self-use
        return ''

    def _get_query_params(self):
        # pylint: disable=no-self-use
        return {}

    def _get_method(self):
        # pylint: disable=no-self-use
        return 'GET'

    def _get_body(self):
        # pylint: disable=no-self-use
        return None

    def _get_headers(self):
        # pylint: disable=no-self-use
        return None

    def execute(self):
        """Fetches HTTP response and returns processed result

           Sends the query-request to the OData service, returning a client-side Enumerable for
           subsequent in-memory operations.

           Fetches HTTP response and returns processed result"""

        url = self._url.rstrip('/') + '/' + self._get_path()
        body = self._get_body()

        headers = {} if self._headers is None else self._headers
        headers.update(self._get_headers())

        self._logger.debug('execute %s request to %s', self._get_method(), url)
        self._logger.debug('  query params: %s', self._get_query_params())
        self._logger.debug('  headers: %s', headers)
        if body:
            self._logger.debug('  body: %s', body)

        response = self._conn.request(
            self._get_method(),
            url,
            headers=headers,
            params=self._get_query_params(),
            data=body)

        self._logger.debug('  url: %s', response.url)
        self._logger.debug('  status code: %d', response.status_code)
        self._logger.debug('  body: %s', response.content)

        return self._handler(response)


class EntityGetRequest(ODataHttpRequest):
    """Used for GET operations of a single entity"""

    def __init__(self, url, connection, handler, last_segment, entity_key):
        super(EntityGetRequest, self).__init__(url, connection, handler)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._entity_key = entity_key
        self._select = None
        self._expand = None
        self._last_segment = last_segment

        self._logger.debug('New instance of EntityGetRequest for last segment: %s', self._last_segment)

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

    def _get_path(self):
        return self._last_segment + self._entity_key.to_key_string()

    def _get_headers(self):
        return {'Accept': 'application/json'}

    def _get_query_params(self):
        qparams = super(EntityGetRequest, self)._get_query_params()

        if self._select is not None:
            qparams['$select'] = self._select

        if self._expand is not None:
            qparams['$expand'] = self._expand

        return qparams


class EntityCreateRequest(ODataHttpRequest):
    """Used for creating entities (POST operations of a single entity)

       Call execute() to send the create-request to the OData service
       and get the newly created entity."""

    def __init__(self, url, connection, handler, entity_set):
        super(EntityCreateRequest, self).__init__(url, connection, handler)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._entity_set = entity_set
        self._entity_type = entity_set.entity_type

        self._values = {}

        # get all properties declared by entity type
        self._type_props = self._entity_type.proprties()

        self._logger.debug('New instance of EntityCreateRequest for entity type: %s', self._entity_type.name)

    def _get_path(self):
        return self._entity_set.name

    def _get_method(self):
        # pylint: disable=no-self-use
        return 'POST'

    def _get_body(self):
        # pylint: disable=no-self-use
        body = {}
        for key, val in self._values.iteritems():
            body[key] = val
        return json.dumps(body)

    def _get_headers(self):
        return {
            'Accept': 'application/json',
            'Content-type': 'application/json'
        }

    def set(self, **kwargs):
        """Set properties on the new entity."""
        # TODO: consider use of attset for setting properties

        self._logger.info(kwargs)

        for key, val in kwargs.iteritems():
            try:
                self._entity_type.proprty(key)
            except KeyError:
                raise PyODataException('Property {} is not declared in {} entity type'.format(
                    key, self._entity_type.name))

            self._values[key] = val

        return self


class EntityModifyRequest(ODataHttpRequest):
    """Used for modyfing entities (UPDATE/MERGE operations on a single entity)

       Call execute() to send the update-request to the OData service
       and get the modified entity."""

    def __init__(self, url, connection, handler, entity_set, entity_key):
        super(EntityModifyRequest, self).__init__(url, connection, handler)
        self._logger = logging.getLogger(LOGGER_NAME)
        self._entity_set = entity_set
        self._entity_type = entity_set.entity_type
        self._entity_key = entity_key

        self._values = {}

        # get all properties declared by entity type
        self._type_props = self._entity_type.proprties()

        self._logger.debug('New instance of EntityModifyRequest for entity type: %s', self._entity_type.name)

    def _get_path(self):
        return self._entity_set.name + self._entity_key.to_key_string()

    def _get_method(self):
        # pylint: disable=no-self-use
        return 'PATCH'

    def _get_body(self):
        # pylint: disable=no-self-use
        body = {}
        for key, val in self._values.iteritems():
            body[key] = val
        return json.dumps(body)

    def _get_headers(self):
        return {
            'Accept': 'application/json',
            'Content-type': 'application/json'
        }

    def set(self, **kwargs):
        """Set properties to be changed."""

        self._logger.info(kwargs)

        for key, val in kwargs.iteritems():
            try:
                self._entity_type.proprty(key)
            except KeyError:
                raise PyODataException('Property {} is not declared in {} entity type'.format(
                    key, self._entity_type.name))

            self._values[key] = val

        return self


class QueryRequest(ODataHttpRequest):
    """INTERFACE A consumer-side query-request builder. Call execute() to issue the request."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, url, connection, handler, last_segment):
        super(QueryRequest, self).__init__(url, connection, handler)

        self._logger = logging.getLogger(LOGGER_NAME)
        self._top = None
        self._skip = None
        self._order_by = None
        self._filter = None
        self._select = None
        self._expand = None
        self._last_segment = last_segment
        self._customs = {}    # string -> string hash
        self._logger.debug('New instance of QueryRequest for last segment: %s', self._last_segment)

    def custom(self, name, value):
        """Adds a custom name-value pair."""
        # returns QueryRequest
        self._customs[name] = value
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

    def _get_path(self):
        # print('last segment {}'.format(self._last_segment))
        return self._last_segment

    def _get_headers(self):
        return {
            'Accept': 'application/json',
        }

    def _get_query_params(self):
        qparams = super(QueryRequest, self)._get_query_params()

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

        for key, val in self._customs.iteritems():
            qparams[key] = val

        if self._expand is not None:
            qparams['$expand'] = self._expand

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
            self.custom(param.name, param.typ.traits.to_odata(value))
        except KeyError:
            raise PyODataException('Function import {0} does not have pararmeter {1}'
                                   .format(self._function_import.name, name))

        return self

    def _get_method(self):
        return self._function_import.http_method

    def _get_headers(self):
        return {
            'Accept': 'application/json',
        }


class EntityProxy(object):
    """An immutable OData entity instance, consisting of an identity (an
       entity-set and a unique entity-key within that set), properties (typed,
       named values), and links (references to other entities).
    """

    # pylint: disable=too-many-branches,too-many-nested-blocks

    def __init__(self, service, entity_set, entity_type, proprties=None, entity_key=None):
        self._logger = logging.getLogger(LOGGER_NAME)
        self._service = service
        self._entity_set = entity_set
        self._entity_type = entity_type
        self._key_props = entity_type.key_proprties
        self._cache = dict()
        self._entity_key = entity_key

        self._logger.debug('New entity proxy instance of type %s from properties: %s', entity_type.name, proprties)

        # cache values of individual properties if provided
        if proprties is not None:

            # first, cache values of direct properties
            for type_proprty in self._entity_type.proprties():
                if type_proprty.name in proprties:
                    self._cache[type_proprty.name] = proprties[type_proprty.name]

            # then, assign all navigation properties
            for prop in self._entity_type.nav_proprties:

                if prop.name in proprties:

                    # entity type of navigation property
                    prop_etype = prop.to_role.entity_type

                    # cache value according to multiplicity
                    if prop.to_role.multiplicity in \
                        [pyodata.v2.model.EndRole.MULTIPLICITY_ONE,
                         pyodata.v2.model.EndRole.MULTIPLICITY_ZERO_OR_ONE]:

                        # cache None in case we receive nothing (null) instead of entity data
                        if proprties[prop.name] is None:
                            self._cache[prop.name] = None
                        else:
                            self._cache[prop.name] = EntityProxy(
                                service,
                                None,
                                prop_etype,
                                proprties[prop.name])

                    elif prop.to_role.multiplicity == pyodata.v2.model.EndRole.MULTIPLICITY_ZERO_OR_MORE:
                        # default value is empty array
                        self._cache[prop.name] = []

                        # if there are no entities available, received data consists of
                        # metadata properties only.
                        if 'results' in proprties[prop.name]:

                            # available entities are serialized in results array
                            for entity in proprties[prop.name]['results']:
                                self._cache[prop.name].append(EntityProxy(
                                    service,
                                    None,
                                    prop_etype,
                                    entity))
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
                                     .format(self._entity_type.name, attr, ex.message))

    def get_proprty(self, name, connection=None):
        """Returns value of the property"""

        self._logger.info('Initiating property request for %s', name)

        def proprty_get_handler(key, proprty, response):
            """Gets property value from HTTP Response"""

            if response.status_code != requests.codes.ok:
                raise HttpError('HTTP GET for Attribute {0} of Entity {1} failed with status code {2}'
                                .format(proprty.name, key, response.status_code), response)

            data = response.json()['d']
            return proprty.typ.traits.from_odata(data[proprty.name])

        path = '{0}({1})'.format(self._entity_set._name, self._entity_key.to_key_string())   # pylint: disable=protected-access

        return self._service.http_get_odata('{0}/{1}'.format(path, name),
                                            partial(proprty_get_handler,
                                                    path,
                                                    self._entity_type.proprty(name)),
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

        return self._service.url.rstrip('/') + '/' + self._entity_set._name + self._entity_key.to_key_string()  # pylint: disable=protected-access


class EntitySetProxy(object):
    """EntitySet Proxy"""

    def __init__(self, service, entity_set):
        self._service = service
        self._entity_set = entity_set
        self._name = entity_set.name
        self._key = entity_set.entity_type.key_proprties
        self._logger = logging.getLogger(LOGGER_NAME)

        self._logger.debug('New entity set proxy instance for %s', self._name)

    def get_entity(self, key=None, **args):
        """Get entity based on provided key properties"""

        def get_entity_handler(response):
            """Gets entity from HTTP response"""

            if response.status_code != requests.codes.ok:
                raise HttpError('HTTP GET for Entity {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity = response.json()['d']

            return EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, entity)

        key = EntityKey(self._entity_set.entity_type, key, **args)

        self._logger.info('Getting entity %s for key %s and args %s', self._entity_set.entity_type.name, key, args)

        return EntityGetRequest(
            self._service.url,
            self._service.connection,
            get_entity_handler,
            self._entity_set.name,
            key)

    def get_entities(self):
        """Get all entities"""

        def get_entities_handler(response):
            """Gets entity set from HTTP Response"""

            if response.status_code != requests.codes.ok:
                raise HttpError('HTTP GET for Entity Set {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entities = response.json()['d']['results']

            result = []
            for props in entities:
                entity = EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, props)
                result.append(entity)

            return result

        return QueryRequest(
            self._service.url,
            self._service.connection,
            get_entities_handler,
            self._name)

    def create_entity(self, return_code=requests.codes.created):
        """Creates a new entity in the given entity-set."""

        def create_entity_handler(response):
            """Gets newly created entity encoded in HTTP Response"""

            if response.status_code != return_code:
                raise HttpError('HTTP POST for Entity Set {0} failed with status code {1}'
                                .format(self._name, response.status_code), response)

            entity_props = response.json()['d']

            return EntityProxy(self._service, self._entity_set, self._entity_set.entity_type, entity_props)

        return EntityCreateRequest(
            self._service.url,
            self._service.connection,
            create_entity_handler,
            self._entity_set)

    def update_entity(self, key=None, **kwargs):
        """Updates an existing entity in the given entity-set."""

        def update_entity_handler(response):
            """Gets modified entity encoded in HTTP Response"""

            if response.status_code != 204:
                raise HttpError('HTTP {0} for Entity Set {1} failed with status code {2}'
                                .format(response.request.method, self._name, response.status_code), response)

        key = EntityKey(self._entity_set.entity_type, key, **kwargs)

        self._logger.info('Updating entity %s for key %s and args %s', self._entity_set.entity_type.name, key, kwargs)

        return EntityModifyRequest(
            self._service.url,
            self._service.connection,
            update_entity_handler,
            self._entity_set,
            key)


# pylint: disable=too-few-public-methods
class EntityContainer(object):
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
            raise AttributeError('EntitySet {0} not defined in {1}.'.format(name, ','.join(self._entity_sets.keys())))


class FunctionContainer(object):
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
            raise AttributeError('Function {0} not defined in {1}.'.format(name, ','.join(self._functions.keys())))

        fimport = self._service.schema.function_import(name)

        def function_import_handler(fimport, response):
            """Get function call response from HTTP Response"""

            if response.status_code != requests.codes.ok:
                raise HttpError('Function import call failed with status code {0}'
                                .format(response.status_code), response)

            response_data = response.json()['d']

            # 1. if return types is "entity type", return instance of appropriate entity proxy
            if isinstance(fimport.return_type, pyodata.v2.model.EntityType):
                return EntityProxy(self._service, fimport.entity_set_name, fimport.return_type, response_data)

            # 2. return raw data for all other return types (primitives, complex types encoded in dicts, etc.)
            return response_data

        return FunctionRequest(
            self._service.url,
            self._service.connection,
            partial(function_import_handler, fimport),
            fimport)


class Service(object):
    """OData service"""

    def __init__(self, url, schema, connection):
        self._url = url
        self._schema = schema
        self._connection = connection
        self._entity_container = EntityContainer(self)
        self._function_container = FunctionContainer(self)

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
    def entity_sets(self):
        """EntitySet proxy"""

        return self._entity_container

    @property
    def functions(self):
        """Functions proxy"""

        return self._function_container

    def http_get(self, path, connection=None):
        """HTTP GET response for the passed path in the service"""

        conn = connection
        if conn is None:
            conn = self._connection

        return conn.get('{0}/{1}'.format(self._url, path))

    def http_get_odata(self, path, handler, connection=None):
        """HTTP GET request proxy for the passed path in the service"""

        conn = connection
        if conn is None:
            conn = self._connection

        return ODataHttpRequest(
            '{0}/{1}'.format(self._url, path),
            conn,
            handler,
            headers={'Accept': 'application/json'})
