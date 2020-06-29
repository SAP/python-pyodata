Updating
========

To update an entity, you must create an updated request, set properties to the
values you want and execute the request. The library will send an HTTP PATCH
request to the remote service.

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

    northwind = pyodata.Client(SERVICE_URL, requests.Session())

    update_request = northwind.entity_sets.Customers.update_entity(CustomerID='ALFKI')
    update_request.set(CompanyName='Alfons Kitten')
    update_request.execute()


In the case the service you are dealing with requires PUT method, you have two options.

The first option allows you to change the used HTTP method for a single call via
the key word parameter *method* of the method *update_entity*.

.. code-block:: python

    update_request = northwind.entity_sets.Customers.update_entity(CustomerID='ALFKI', method='PUT')

If you need to run more update requests for different entity sets and all of them must be *PUT*,
then you can consider setting the default service's update method to *PUT*.

.. code-block:: python

    northwind.config['http']['update_method'] = 'PUT'
