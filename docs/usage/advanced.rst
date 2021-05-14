Advanced usage
==============

Batch requests
--------------

Example of batch request that contains 3 simple entity queries:

.. code-block:: python

    batch = northwind.create_batch()

    batch.add_request(northwind.entity_sets.Employees.get_entity(108))
    batch.add_request(northwind.entity_sets.Employees.get_entity(234))
    batch.add_request(northwind.entity_sets.Employees.get_entity(23))

    response = batch.execute()

    print(response[0].EmployeeID, response[0].LastName)
    print(response[1].EmployeeID, response[1].LastName)
    print(response[2].EmployeeID, response[2].LastName)


Example of batch request that contains simple entity query as well
as changest consisting of two requests for entity modification:

.. code-block:: python

    batch = northwind.create_batch()

    batch.add_request(northwind.entity_sets.Employees.get_entity(108))

    changeset = northwind.create_changeset()

    changeset.add_request(northwind.entity_sets.Employees.update_entity(45).set(LastName='Douglas'))

    batch.add_request(changeset)

    response = batch.execute()

    print(response[0].EmployeeID, response[0].LastName)


Error handling
--------------

PyOData returns *HttpError* when the response code does not match the expected
code. Basically the exception is raised for all status codes >= 400 and its
instances have the property response which holds return value of the library
making HTTP requests.

For example, the following code show how to print out error details if
Python Requests is used as the HTTP communication library.

.. code-block:: python

    try:
        new_data = create_request.execute()
    except pyodata.exceptions.HttpError as ex:
        print(ex.response.text)

In the case you know the implementation of back-end part and you want to show
accurate errors reported by your service, you can replace *HttpError* by your
sub-class *HttpError* by assigning your type into the class member *VendorType* of
the class *HttpError*.

.. code-block:: python

    from pyodata.exceptions import HttpError

    class MyHttpError(HttpError):

        def __init__(self, message, response):
            super(MyHttpError, self).__init__('Better message', response)


    HttpError.VendorType = MyHttpError


The class *pyodata.vendor.SAP.BusinessGatewayError* is an example of such
an HTTP error handling.

Enable Logging
--------------

.. _Python logging: https://docs.python.org/3/library/logging.html

The library uses `Python logging`_ without own handler, so to enable logging
it is enough to set log level to the desired value.

.. code-block:: python

    import logging

    logging.basicConfig()
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

Observing HTTP traffic
----------------------

There are cases where you need access to the transport protocol (http). For
example: you need to read value of specific http header. Pyodata provides
simple mechanism to observe all http requests and access low level properties
from underlying network library (e.g. **python requests**).

You can use basic predefined observer class
``pyodata.utils.RequestObserverLastCall`` to catch last response headers:

.. code-block:: python

    from pyodata.utils import RequestObserverLastCall

    last = RequestObserverLastCall()
    northwind.entity_sets.Employees.get_entity(1).execute(last)
    print(last.response.headers)

You can also write your own observer to cover more specific cases. This is an example of
custom observer which stores status code of the last response.

.. code-block:: python

    from pyodata.utils import RequestObserver

    class CatchStatusCode(RequestObserver):

        def __init__(self):
            self.status_code = None

        def http_response(self, response, request):
            self.status_code = response.status_code

    last_status = RequestObserverLastCall()

    northwind.entity_sets.Employees.get_entity(1).execute(last_status)
    print(last_status.status_code)
