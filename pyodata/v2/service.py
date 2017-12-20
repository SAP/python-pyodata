"""OData service implementation"""

from functools import partial
import requests
from pyodata.exceptions import HttpError


class ODataHttpRequest(object):
    """Deferred HTTP Request"""

    def __init__(self, url, connection, handler):
        self._conn = connection
        self._url = url
        self._handler = handler

    def execute(self):
        """Fetches HTTP response and returns processed result"""

        response = self._conn.get(self._url, headers={'Accept': 'application/json'})
        return self._handler(response)


class EntityProxy(object):
    """Entity proxy"""

    def __init__(self, service, entity_type, identifier, proprties=None):
        self._service = service
        self._entity_type = entity_type
        self._identifier = identifier

        if proprties is not None:
            self._cache = proprties
        else:
            self._cache = dict()

    def __repr__(self):
        return self._identifier

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

        def proprty_get_handler(identifier, proprty, response):
            """Gets property value from HTTP Response"""

            if response.status_code != requests.codes.ok:
                raise HttpError('HTTP GET for Attribute {0} of Entity {1} failed with status code {2}'
                                .format(proprty.name, identifier, response.status_code), response)

            data = response.json()['d']
            return proprty.typ.traits.from_odata(data[proprty.name])

        return self._service.http_get_odata('{0}/{1}'.format(self._identifier, name),
                                            partial(proprty_get_handler,
                                                    self._identifier,
                                                    self._entity_type.proprty(name)),
                                            connection=connection)

    @property
    def url(self):
        """URL of the real entity"""

        if self._url is None:
            # TODO: in the future, build the URL from Service URL,
            # EntitySet name, and keys
            raise NotImplementedError

        return self._url


class EntitySetProxy(object):
    """EntitySet Proxy"""

    def __init__(self, service, entity_set):
        self._service = service

        self._entity_set = entity_set
        self._name = entity_set.name
        self._key = entity_set.entity_type.key_proprties
        self._key_length = len(self._key)

    def _build_key(self, args):
        if len(args) != self._key_length:
            raise RuntimeError('Key has {0} properties but {1} were given'.format(self._key_length, len(args)))

        return ','.join(('{0}={1}'.format(key.name, key.typ.traits.to_odata(args[i]))
                         for i, key in enumerate(self._key)))

    def get_entity(self, *args):
        """EntitySet GET Entity"""

        key_part = self._build_key(args)
        identifier = '{0}({1})'.format(self._name, key_part)

        return EntityProxy(self._service, self._entity_set.entity_type, identifier)


#pylint: disable=too-few-public-methods
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
