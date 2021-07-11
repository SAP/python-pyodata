"""SAP extensions to OData protocol"""

import json
import logging
from pyodata.exceptions import HttpError


def json_get(obj, member, typ, default=None):
    """Tries to get the passed member from the passed JSON object obj and makes
       sure it is instance of the passed typ.

       If the passed member is not found the default is returned instead.

       If the typ is not matched the exception ValueError is raised.
    """

    if not isinstance(obj, dict):
        raise ValueError('the passed JSON is not a dict')

    value = obj.get(member, default)
    if not isinstance(value, typ):
        raise ValueError(f'{member} is not a {typ.__name__}')

    return value


def add_btp_token_to_session(session, key, user, password):
    """Using the provided credentials, the function tries to add the
       necessary token for establishing a connection to an OData service
       coming from SAP BTP, ABAP environment.

       If any of the provided credentials are invalid, the server will
       respond with 401, and the function will raise HttpError.
    """
    token_url = key['uaa']['url'] + f'/oauth/token?grant_type=password&username={user}&password={password}'
    token_response = session.post(token_url, auth=(key['uaa']['clientid'], key['uaa']['clientsecret']))

    if token_response.status_code != 200:
        raise HttpError(
            f'Token request failed, status code: {token_response.status_code}, body:\n{token_response.content}',
            token_response)

    token_response = json.loads(token_response.text)
    token = token_response['id_token']

    session.headers.update({'Authorization': f'Bearer {token}'})
    return session


class BusinessGatewayError(HttpError):
    """To display the right error message"""

    def __init__(self, message, response):
        """Try to parse the response as JSON
           and get the error message from BG
        """

        logging.debug('SAP BusinessGateway HTTP Error parser')

        errordetails = []

        try:
            data = json.loads(response.content.decode('utf-8'))

            error = json_get(data, 'error', dict, {})
            innererror = json_get(error, 'innererror', dict, {})

            message = json_get(json_get(error, 'message', dict, {}),
                               'value', str, message)

            errordetails = [json_get(detail, 'message', str, '')
                            for detail
                            in json_get(innererror, 'errordetails', list, [])]
        except ValueError as ex:
            logging.debug(
                'The HTTP error is not a SAP BusinessGateway JSON error')
            logging.debug('JSON parsing error: %s', str(ex))

        super(BusinessGatewayError, self).__init__(message, response)

        self.errordetails = errordetails
