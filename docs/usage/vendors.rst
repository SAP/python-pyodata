Vendor-specific helpers
==============

This document presents the helpers found in ``pyodata.vendor`` 

Get the service proxy client for an OData service published on SAP BTP, ABAP environment
--------------------------------------------------------------------------

Let's assume you have an ABAP environment service instance running on SAP Business Technology
Platform. You have used this instance to provide an OData service by using, for example, the
ABAP RESTful Application Programming Model. To connect to it, you need to provide several attributes 
found in the JSON service key of the instance, as well as your username and password for SAP BTP.

``pyodata.vendor.SAP`` offers a helper that takes the arguments described above, as well as an
existing ``requests.Session`` object (or another one conforming to the same API), and adds the
required token to the session object's authorization header.

The following code demonstrates using the helper.

.. code-block:: python
  
  import pyodata
  from pyodata.vendor import SAP
  import requests
  import json

  with open('key.txt', 'r') as f:
      KEY = json.loads(f.read())

  USER = "MyBtpUser"
  PASSWORD = "MyBtpPassword"
  SERVICE_URL = KEY["url"] + "/sap/opu/odata/sap/" + "ZMyBtpService"

  session = SAP.add_btp_token_to_session(requests.Session(), KEY, USER, PASSWORD)
  # do something more with session object if necessary (e.g. adding sap-client parameter, or CSRF token)
  client = pyodata.Client(SERVICE_URL, session)

Detecting SAP domain errors in response headers
------------------------------------------------

Some SAP OData services signal domain errors via the ``sap-message`` response header on
otherwise-200 responses. pyodata's domain handler never sees these headers, so callers
cannot detect the error through the normal return value.

``pyodata.vendor.SAP`` provides a ready-made stateless hook, ``sap_header_error_hook``,
that reads the ``sap-message`` header, parses it as JSON, and raises ``BusinessGatewayError``
when the ``severity`` field equals ``"error"``. Pass it as the ``response_hook`` argument to
``Client`` (or directly to ``Service``):

.. code-block:: python

  import pyodata
  from pyodata.vendor.SAP import sap_header_error_hook
  import requests

  SERVICE_URL = 'https://example.com/sap/opu/odata/sap/ZMyService'

  session = requests.Session()
  client = pyodata.Client(SERVICE_URL, session, response_hook=sap_header_error_hook)

  try:
      result = client.entity_sets.Employees.get_entity(1).execute()
  except pyodata.vendor.SAP.BusinessGatewayError as ex:
      print(f"SAP domain error: {ex}")

The hook fires before pyodata's domain handler, so the exception propagates before any
result object is constructed. It is safe under concurrent and async use because it holds
no instance state.
