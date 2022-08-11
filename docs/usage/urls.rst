URLs generation
===============

.. _Locust: https://docs.locust.io/en/stable/

Sometimes you may want to not use **PyOData** to actually make the HTTP requests, but
just grab the url and body for some other library. For that, you can use following
methods from ODataHttpRequest class - which is base of every query, update or delete
covered in pyodata documentation.

.. code-block:: python

  .get_method()
  .get_path()
  .get_query_params()
  .get_body()

Locust integration example
--------------------------
**Warning** - execute load testing scripts only against service you own!

Following is example of integration of pyodata as url provider for Locust_ load testing tool.

.. code-block:: python

  import requests
  import pyodata
  import os  
  from locust import HttpUser, task, between
  
  SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'
  
  odataClient = pyodata.Client(SERVICE_URL, requests.Session())
  smith_employees_query = odataClient.entity_sets.Employees.get_entities().filter("FirstName eq 'John' and LastName eq 'Smith'")

  class MyUser(HttpUser):
      wait_time = between(5, 15)
      host = SERVICE_URL

      @task(1)
      def filter_query(self):
          urlpath = smith_employees_query.get_path()
          url = os.path.join(SERVICE_URL,urlpath)
          params = smith_employees_query.get_query_params()
          self.client.get(url,params=params)
