"""OData Client Implementation"""

import logging

import pyodata.v2.model
import pyodata.v2.service
from pyodata.exceptions import PyODataException, HttpError


class Client:
    """OData service client"""

    # pylint: disable=too-few-public-methods

    ODATA_VERSION_2 = 2

    def __new__(cls, url, connection, odata_version=ODATA_VERSION_2):
        """Create instance of the OData Client for given URL"""

        logger = logging.getLogger('pyodata.client')

        if odata_version == Client.ODATA_VERSION_2:

            # sanitize url
            url = url.rstrip('/') + '/'

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
            if mime_type not in ['application/xml', 'text/xml']:
                raise HttpError(
                    'Metadata request did not return XML, MIME type: {}, body:\n{}'.format(mime_type, resp.content),
                    resp)

            # create model instance from received metadata
            logger.info('Creating OData Schema (version: %d)', odata_version)
            schema = pyodata.v2.model.schema_from_xml(resp.content)

            # create service instance based on model we have
            logger.info('Creating OData Service (version: %d)', odata_version)
            service = pyodata.v2.service.Service(url, schema, connection)

            return service

        raise PyODataException('No implementation for selected odata version {}'.format(odata_version))
