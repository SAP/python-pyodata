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
    
Dynamically referenced EntitySet
------------------------------------------------

If you need to work with many Entity Sets the same way or if you just need to pick up the used Entity Set name in run-time, you may find out the ability to get an instance of Entity Set proxy dynamically. Here is an example of how you can print a count of all employees:

.. code-block:: python

    count = getattr(northwind.entity_sets, 'Employees').get_entities().count().execute()
    print(count)

Inspecting responses with a hook
---------------------------------

Some OData services communicate domain errors via HTTP response headers on otherwise-200
responses. Because pyodata discards headers before returning the domain result, callers
cannot detect these errors through the normal return value.

``Client`` (and ``Service`` directly) accept an optional ``response_hook`` parameter — a
``Callable[[response], None]`` that fires before the domain handler runs, for every request
type (including ``async_execute()``). The hook receives the raw response object. Raising an
exception from the hook propagates to the caller and prevents the domain handler from running.

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'https://odata.example.com/MyService.svc'

    def my_hook(response):
        if response.headers.get('x-custom-error'):
            raise RuntimeError(f"Service signalled error: {response.headers['x-custom-error']}")

    service = pyodata.Client(SERVICE_URL, requests.Session(), response_hook=my_hook)

The hook must be stateless to be safe under concurrent and async use. If you need to
handle SAP-specific header errors, use the ready-made hook in ``pyodata.vendor.SAP``
— see :doc:`vendors`.

Out-of-range JSON dates
-----------------------

Some services return JSON ``/Date(...)/`` values outside the range Python's
``datetime`` can represent. By default, PyOData raises
``pyodata.exceptions.PyODataModelError`` rather than silently replacing them.
The supported millisecond range is ``-62135596800000`` through
``253402300799999``, inclusive.

If your service deliberately uses such values as minimum/maximum date sentinels,
you can enable either workaround independently before reading entity responses:

.. code-block:: python

    import pyodata.v2.model as model

    model.FIX_SCREWED_UP_MINIMAL_DATETIME_VALUE = True
    model.FIX_SCREWED_UP_MAXIMUM_DATETIME_VALUE = True

Both flags default to ``False``. They apply to JSON decoding of ``Edm.DateTime``
and ``Edm.DateTimeOffset`` values, not to malformed date strings or date literals
in URLs. Values already within the supported range are not changed.

* ``FIX_SCREWED_UP_MINIMAL_DATETIME_VALUE`` replaces values below the minimum
  with January 1, year 1 at midnight.
* ``FIX_SCREWED_UP_MAXIMUM_DATETIME_VALUE`` replaces values above the maximum
  with December 31, year 9999 at midnight. This is **not** ``datetime.max``
  (the end of that day).

For example, with both flags enabled:

.. code-block:: python

    dates = model.Types.from_name('Edm.DateTime').traits
    print(dates.from_json('/Date(-62135596800001)/'))
    # 0001-01-01 00:00:00+00:00
    print(dates.from_json('/Date(253402300800000)/'))
    # 9999-12-31 00:00:00+00:00

The timezone supplied by the decoder is retained, including the offset for
``Edm.DateTimeOffset``. These are module-level settings shared by all clients
in the process, not per-client options. Configure only the flags needed by your
service when your application starts; avoid toggling them around concurrent
requests. Set a flag back to ``False`` to restore strict range checking.
