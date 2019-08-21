Creating
========

.. _CSRF: https://en.wikipedia.org/wiki/Cross-site_request_forgery
.. _Requests: https://2.python-requests.org/en/master/

The create action executes the HTTP method POST which is usually protected by
CSRF_ and therefore you must make some effort to initialize your HTTP Session
to send POST requests acceptable by the remote server.

Let's assume you use the python library Requests_

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'http://example.io/TheServiceRoot/'

    session = requests.Session()
    response = session.head(SERVICE_URL, headers={'x-csrf-token': 'fetch'})
    token = response.headers.get('x-csrf-token', '')
    session.headers.update({'x-csrf-token': token})

    theservice = pyodata.Client(SERVICE_URL, session)


Create an entity with a complex type property
---------------------------------------------

You need to use the method set which accepts key value parameters:

.. code-block:: python

    employee_data = {
        'FirstName': 'Mark',
        'LastName': 'Goody',
        'Address': {
            'HouseNumber': 42,
            'Street': 'Paradise',
            'City': 'Heaven'
        }
    }

    create_request = northwind.entity_sets.Employees.create_entity()
    create_request.set(**employee_data)

    new_employee_entity = create_request.execute()


or you can do it explicitly:

.. code-block:: python

    create_request = northwind.entity_sets.Employees.create_entity()
    create_request.set(
        FirstName='Mark',
        LastName='Goody',
        Address={
            'HouseNumber': 42,
            'Street': 'Paradise',
            'City': 'Heaven'
        }
    )

    new_employee_entity = request.execute()
