Initialization
==============

.. _Requests: https://requests.readthedocs.io/en/latest/
.. _Session: https://requests.readthedocs.io/en/latest/user/advanced/#session-objects

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

Get the service proxy client for an OData service requiring sap-client parameter
--------------------------------------------------------------------------------

This is a sample when it is necessary to specify sap-client:

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

    session = requests.Session()
    param = {'sap-client': '510'}
    session.params = param
    northwind = pyodata.Client(SERVICE_URL, session)

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

Get the service with local metadata
-----------------------------------

It may happen that you will have metadata document for your service downloaded
in a local file and you will want to initialize the service proxy from this
file. In such a case you can provide content of the file as the named argument
`metadata`. Please, make sure you provide `bytes` and not `str` (required by
the xml parser lxml).

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

    with open('/the/file/path.xml', 'rb') as mtd_file:
        local_metadata = mtd_file.read()

    northwind = pyodata.Client(SERVICE_URL, requests.Session(), metadata=local_metadata)

Dealing with errors during parsing metadata
-------------------------------------------

In the case where you need to consume a service which has not fully valid metadata document and is not under your control, you can configure the metadata parser to try to recover from detected problems.

Parser recovery measures include actions such as using a stub entity type if the parser cannot find a referenced entity type. The stub entity type allows the parser to continue processing the given metadata but causes fatal errors when accessed from the client.

Class config provides easy to use wrapper for all parser configuration. These are:
    - XML namespaces
    - Parser policies (how parser act in case of invalid XML tag). We now support three types of policies:
        - Policy fatal - the policy raises exception and terminates the parser
        - Policy warning - the policy reports the detected problem, executes a fallback code and then continues normally
        - Policy ignore - the policy executes a fallback code without reporting the problem and then continues normally

Parser policies can be specified individually for each XML tag (See enum ParserError for more details). If no policy is specified for the tag, the default policy is used.

For parser to use your custom configuration, it needs to be passed as an argument to the client.

.. code-block:: python

    import pyodata
    from pyodata.v2.model import PolicyFatal, PolicyWarning, PolicyIgnore, ParserError, Config
    import requests

    SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

    namespaces = {
        'edmx': 'customEdmxUrl.com',
        'edm': 'customEdmUrl.com'
    }

    custom_config = Config(
        xml_namespaces=namespaces,
        default_error_policy=PolicyFatal(),
        custom_error_policies={
             ParserError.ANNOTATION: PolicyWarning(),
             ParserError.ASSOCIATION: PolicyIgnore()
        })

    northwind = pyodata.Client(SERVICE_URL, requests.Session(), config=custom_config)

Additionally, Schema class has Boolean atribute 'is_valid' that returns if the parser encountered errors. It's value does not depends on used Parser policy. 

.. code-block:: python

    northwind.schema.is_valid

Prevent substitution by default values
--------------------------------------

Per default, missing properties get filled in by type specific default values. While convenient, this throws away
the knowledge of whether a value was missing in the first place.
To prevent this, the class config mentioned in the section above takes an additional parameter, `retain_null`.

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

    northwind = pyodata.Client(SERVICE_URL, requests.Session(), config=pyodata.v2.model.Config(retain_null=True))

    unknown_shipped_date = northwind.entity_sets.Orders_Qries.get_entity(OrderID=11058,
                                                                         CompanyName='Blauer See Delikatessen').execute()

    print(
        f'Shipped date: {"unknown" if unknown_shipped_date.ShippedDate is None else unknown_shipped_date.ShippedDate}')

Changing `retain_null` to `False` will print `Shipped date: 1753-01-01 00:00:00+00:00`.

Set custom namespaces (Deprecated - use config instead)
-------------------------------------------------------

Let's assume you need to work with a service  which uses namespaces not directly supported by this library e. g. ones
hosted on private urls such as *customEdmxUrl.com* and *customEdmUrl.com*:

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

    namespaces = {
        'edmx': 'customEdmxUrl.com'
        'edm': 'customEdmUrl.com'
    }

    northwind = pyodata.Client(SERVICE_URL, requests.Session(), namespaces=namespaces)
