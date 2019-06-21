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

Get the service proxy client for an OData service requiring Certificate authentication
--------------------------------------------------------------------------------------

Let's assume your service requires certificate based authentication and you are
able to export the certificate into the file *mycert.p12*. You need to split
the certificate into public key, private key and certificate authority key.

The following steps has been verified on Fedora Linux and Mac OS.

.. code-block:: bash

    openssl pkcs12 -in mycert.p12 -out ca.pem -cacerts -nokeys
    openssl pkcs12 -in mycert.p12 -out client.pem -clcerts -nokeys
    openssl pkcs12 -in mycert.p12 -out key.pem -nocerts
    openssl rsa -in key.pem -out key_decrypt.pem

You can verify your steps by curl:

.. code-block:: bash

    curl --key key_decrypt.pem --cacert ca.pem --cert client.pem -k 'SERVICE_URL/$metadata'

Python client initialization:

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'https://odata.example.com/Secret.svc'

    session = requests.Session()
    session.verify = 'ca.pem'
    session.cert = ('client.pem', 'key_decrypt.pem')

    client = pyodata.Client(SERVICE_URL, session)


For more information on client side SSL cerificationcas, please refer to this [gist](https://gist.github.com/mtigas/952344).
