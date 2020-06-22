"""OData Client Implementation"""

import logging
import warnings

from pyodata.config import Config
from pyodata.model.builder import MetadataBuilder
from pyodata.exceptions import PyODataException, HttpError
from pyodata.v2.service import Service
from pyodata.v2 import ODataV2
from pyodata.v4 import ODataV4

import pyodata.v4 as v4


def _fetch_metadata(connection, url, logger):
    # download metadata
    logger.info('Fetching metadata')
    resp = connection.get(url + '$metadata')

    logger.debug('Retrieved the response:\n%s\n%s',
                 '\n'.join((f'H: {key}: {value}' for key, value in resp.headers.items())),
                 resp.content)

    if resp.status_code != 200:
        raise HttpError(
            'Metadata request failed, status code: {}, body:\n{}'.format(resp.status_code, resp.content), resp)

    mime_type = resp.headers['content-type']
    if not any((typ in ['application/xml', 'text/xml'] for typ in mime_type.split(';'))):
        raise HttpError(
            'Metadata request did not return XML, MIME type: {}, body:\n{}'.format(mime_type, resp.content),
            resp)

    return resp.content


class Client:
    """OData service client"""

    # pylint: disable=too-few-public-methods
    def __new__(cls, url, connection, namespaces=None,
                config: Config = None, metadata: str = None):
        """Create instance of the OData Client for given URL"""

        logger = logging.getLogger('pyodata.client')

        # sanitize url
        url = url.rstrip('/') + '/'

        if metadata is None:
            metadata = _fetch_metadata(connection, url, logger)
        else:
            logger.info('Using static metadata')

        if config is not None and namespaces is not None:
            raise PyODataException('You cannot pass namespaces and config at the same time')

        if config is None:
            logger.info('No OData version has been provided. Client defaulted to OData v2')
            config = Config(ODataV2)

        if namespaces is not None:
            warnings.warn("Passing namespaces directly is deprecated. Use class Config instead", DeprecationWarning)
            config.namespaces = namespaces

        # create model instance from received metadata
        logger.info('Creating OData Schema (version: %s)', str(config.odata_version))
        schema = MetadataBuilder(metadata, config=config).build()

        # create service instance based on model we have
        logger.info('Creating OData Service (version: %s)', str(config.odata_version))

        try:
            return {ODataV2: Service,
                    ODataV4: v4.Service}[config.odata_version](url, schema, connection)
        except KeyError:
            raise PyODataException(f'Bug: unhandled OData version {str(config.odata_version)}')
