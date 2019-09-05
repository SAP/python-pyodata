Deleting
========

.. _CSRF: https://en.wikipedia.org/wiki/Cross-site_request_forgery
.. _Requests: https://2.python-requests.org/en/master/

The delete action executes the HTTP method DELETE which is usually protected by
CSRF_ and therefore you must make some effort to initialize your HTTP Session
to send DELETE requests acceptable by the remote server.

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


Deleting an entity
------------------

You can either delete entity by passing its PropertyRef value to the delete function

.. code-block:: python

    request = service.entity_sets.Employees.delete_entity(23)
    request.execute()

or by passing the EntityKey object

.. code-block:: python

    key = EntityKey(service.schema.entity_type('Employee'), ID=23)
    request = service.entity_sets.Employees.delete_entity(key=key)
    request.execute()