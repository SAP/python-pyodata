Querying
========

Get one entity identified by its key value
------------------------------------------

Get employee identified by 1 and print employee first name:

.. code-block:: python

    employee1 = northwind.entity_sets.Employees.get_entity(1).execute()
    print(employee1.FirstName)


Get one entity identified by its key value which is not scalar
--------------------------------------------------------------

Get number of orderd units in the order identified by ProductID 42 and OrderID 10248:

.. code-block:: python

    order = northwind.entity_sets.Order_Details.get_entity(OrderID=10248, ProductID=42).execute()
    print(order.Quantity)


Get all entities of an entity set
---------------------------------

Print unique identification (Id) and last name of all employees:

.. code-block:: python

    employees = northwind.entity_sets.Employees.get_entities().select('EmployeeID,LastName').execute()
    for employee in employees:
        print(employee.EmployeeID, employee.LastName)


Get entities matching a filter
------------------------------

Print unique identification (Id) of all employees with name John Smith:

.. code-block:: python

    smith_employees_request = northwind.entity_sets.Employees.get_entities()
    smith_employees_request = smith_employees_request.filter("FirstName eq 'John' and LastName eq 'Smith'")

    for smith in smith_employees_request.execute():
        print(smith.EmployeeID)


Get entities matching a filter in more Pythonic way
---------------------------------------------------

Print unique identification (Id) of all employees with name John Smith:

.. code-block:: python

    from pyodata.v2.service import GetEntitySetFilter as esf

    smith_employees_request = northwind.entity_sets.Employees.get_entities()
    smith_employees_request = smith_employees_request.filter(esf.and_(
                                                             smith_employees_request.FirstName == 'Jonh',
                                                             smith_employees_request.LastName == 'Smith'))
    for smith in smith_employees_request.execute():
        print(smith.EmployeeID)


Get entities matching a filter in ORM style
---------------------------------------------------

Print unique identification (Id) of all employees with name John Smith:

.. code-block:: python

    from pyodata.v2.service import GetEntitySetFilter as esf

    smith_employees_request = northwind.entity_sets.Employees.get_entities()
    smith_employees_request = smith_employees_request.filter(FirstName="John", LastName="Smith")
    for smith in smith_employees_request.execute():
        print(smith.EmployeeID)


Get entities matching a complex filter in ORM style
---------------------------------------------------

Print unique identification (Id) of all employees with name John Smith:

.. code-block:: python

    from pyodata.v2.service import GetEntitySetFilter as esf

    smith_employees_request = northwind.entity_sets.Employees.get_entities()
    smith_employees_request = smith_employees_request.filter(FirstName__contains="oh", LastName__startswith="Smi")
    for smith in smith_employees_request.execute():
        print(smith.EmployeeID)


Get a count of entities
-----------------------

Print a count of all employees:

.. code-block:: python

    count = northwind.entity_sets.Employees.get_entities().count().execute()
    print(count)

Print all employees and their count:

.. code-block:: python

    employees = northwind.entity_sets.Employees.get_entities().count(inline=True).execute()
    print(employees.total_count)

    for employee in employees:
        print(employee.EmployeeID, employee.LastName)


Get a count of entities via navigation property
-----------------------------------------------

Print a count of all orders associated with Employee 1:

.. code-block:: python

    count = northwind.entity_sets.Employees.get_entity(1).nav('Orders').get_entities().count().execute()
    print(count)


Print all orders associated with Employee 1 and their count:

.. code-block:: python

    orders = northwind.entity_sets.Employees.get_entity(1).nav('Orders').get_entities().count(inline=True).execute()
    print(orders.total_count)

    for order in orders:
        print(order.OrderID, order.ProductID)


Use non-standard OData URL Query parameters
-------------------------------------------

Sometimes services implement extension to OData model and require addition URL
query parameters. In such a case, you can enrich HTTP request made by pyodata with
these parameters by the method `custom(name: str, value: str)`. 

.. code-block:: python

    employee = northwind.entity_sets.Employees.get_entity(1).custom('sap-client', '100').execute()
    
.. code-block:: python

    employees = northwind.entity_sets.Employees.get_entities().custom('sap-client', '100').custom('$skiptoken', 'ABCD').top(10).execute() 
    


(Experimental) Query server-side paginations using the __next field
-------------------------------------------------------------------
Response may contains ony partial listings of the Collection. In this case, "__next" name/value
pair is included, where the value is a URI which identifies the next partial set of entities.


.. code-block:: python

    employees = northwind.entity_sets.Employees.get_entities().select('EmployeeID,LastName').execute()
    while True:
        for employee in employees:
         print(employee.EmployeeID, employee.LastName)

        # Stop if server has no more entities left
        if employees.next_url is None:
          break

        # We got a partial answer - continue with next page
        employees = northwind.entity_sets.Employees.get_entities().next_url(employees.next_url).execute()
