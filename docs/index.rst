.. PyOData documentation master file, created by
   sphinx-quickstart on Sat Jun 15 16:52:02 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PyOData: OData for Pythonistas
==============================

.. image:: https://badge.fury.io/py/pyodata.svg
    :target: https://pypi.org/project/pyodata/

.. image:: https://img.shields.io/pypi/pyversions/pyodata.svg
    :target: https://pypi.org/project/pyodata/

.. image:: https://img.shields.io/pypi/l/pyodata.svg
    :target: https://pypi.org/project/pyodata/

Python agnostic implementation of OData client library.

Supported features
------------------

- OData V2

Basic usage
-----------

.. _Requests: https://2.python-requests.org/en/master/
.. _Session: https://2.python-requests.org/en/master/user/advanced/#session-objects

The only thing you need to do is to import the **pyodata** Python module and
provide an object implementing interface compatible with Session_ from
the library Requests_.

.. code-block:: python

    import pyodata
    import requests

    SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'
    HTTP_LIB = requests.Session()

    northwind = pyodata.Client(SERVICE_URL, HTTP_LIB)

    for customer in northwind.entity_sets.Customers.get_entities().execute():
        print(customer.CustomerID, customer.CompanyName)


The User Guide
--------------

.. toctree::
   :maxdepth: 2

   usage/initialization.rst
   usage/querying.rst
   usage/creating.rst
   usage/updating.rst
   usage/deleting.rst
   usage/function_imports.rst
   usage/metadata.rst
   usage/advanced.rst
   usage/urls.rst
