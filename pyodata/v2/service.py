"""OData service implementation"""

import logging
from functools import partial
import requests
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

            self._logger.info(('Detected single property key, adding pair %s->%s to key'
                               'properties'), key_prop.name, single_key)
        else:
            for key_prop in self._key:
                if key_prop.name not in args:
                    raise PyODataException(
                        'Missing value for key property {}'.format(key_prop.name))

            self._type = EntityKey.TYPE_COMPLEX

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

    def __init__(self, url, connection, handler):
        self._conn = connection
        self._url = url
        self._handler = handler
        self._logger = logging.getLogger(LOGGER_NAME)

    def _get_path(self):
        # pylint: disable=no-self-use
        return ''

    def _get_query_params(self):
        # pylint: disable=no-self-use
        return {}

    def execute(self):
        """Fetches HTTP response and returns processed result

           Sends the query-request to the OData service, returning a client-side Enumerable for
           subsequent in-memory operations.

           Fetches HTTP response and returns processed result"""

        url = self._url.rstrip('/') + '/' + self._get_path()

        self._logger.info('execute GET request to %s', url)
        self._logger.info('  query params %s', self._get_query_params())

        response = self._conn.get(
            url,
            headers={'Accept': 'application/json'},
            params=self._get_query_params())

        self._logger.info('  url: %s', response.url)
        self._logger.info('  status code: %d', response.status_code)
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

        self._logger.info('New instance of EntityGetRequest for last segment: %s', self._last_segment)

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

    def _get_query_params(self):
        qparams = super(EntityGetRequest, self)._get_query_params()

        if self._select is not None:
            qparams['$select'] = self._select

        if self._expand is not None:
            qparams['$expand'] = self._expand

        return qparams


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

        self._logger.info('New instance of QueryRequest for last segment: %s', self._last_segment)

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

    def nav(self, key_value, nav_property):
        """Navigates to a referenced collection using a collection-valued navigation property."""
        # returns QueryRequest
        raise NotImplementedError

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

        for key, val in self._customs:
            qparams[key] = val

        if self._expand is not None:
            qparams['$expand'] = self._expand

        return qparams


class EntityProxy(object):
    """An immutable OData entity instance, consisting of an identity (an
       entity-set and a unique entity-key within that set), properties (typed,
       named values), and links (references to other entities).
    """

    def __init__(self, service, entity_set, entity_type, proprties=None, entity_key=None):
        self._logger = logging.getLogger(LOGGER_NAME)
        self._service = service
        self._entity_set = entity_set
        self._entity_type = entity_type
        self._key_props = entity_type.key_proprties
        self._cache = dict()
        self._entity_key = entity_key

        self._logger.info('New entity proxy instance of type %s from properties: %s', entity_type.name, proprties)

        if proprties is not None:
            for type_proprty in self._entity_type.proprties():
                if type_proprty.name in proprties:
                    self._cache[type_proprty.name] = proprties[type_proprty.name]

        # build entity key if not provided
        if self._entity_key is None:
            # if key seems to be simple (consists of single property)
            if len(self._key_props) == 1:
                self._entity_key = EntityKey(entity_type, self._cache[self._key_props[0].name])
            else:
                # build complex key
                self._entity_key = EntityKey(entity_type, **self._cache)

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

        self._logger.info('New entity set proxy instance for %s', self._name)

    def get_entity(self, key, **args):
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


class Service(object):
    """OData service"""

    def __init__(self, url, schema, connection):
        self._url = url
        self._schema = schema
        self._connection = connection
        self._entity_container = EntityContainer(self)

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

        return ODataHttpRequest('{0}/{1}'.format(self._url, path), conn, handler)
