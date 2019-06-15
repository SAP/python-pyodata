Initialization
==============

.. _Requests: https://2.python-requests.org/en/master/
.. _Session: https://2.python-requests.org/en/master/user/advanced/#session-objects

**PyOData** requires an external HTTP library which has API compatible with
Session_ from Requests_.

Get the service
---------------

Basic initialization which is going to work for everybody:

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

    northwind = pyodata.Client(SERVICE_URL, requests.Session())


Get the service proxy client for an OData service requiring authentication
--------------------------------------------------------------------------

Let's assume you need to work with a service at
the URL *https://odata.example.com/Secret.svc* and User ID is 'MyUser' with
the password 'MyPassword'.

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'https://odata.example.com/Secret.svc'

    session = requests.Session()
    session.auth = ('MyUser', 'MyPassword')

    theservice = pyodata.Client(SERVICE_URL, session)
