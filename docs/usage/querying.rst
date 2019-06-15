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

    for smith in smith_employees.execute():
        print(smith.EmployeeID)


Get entities matching a filter in more Pythonic way
---------------------------------------------------

Print unique identification (Id) of all employees with name John Smith:

.. code-block:: python

    from pyodata.v2.service import GetEntitySetFilter as esf

    smith_employees_request = northwind.entity_sets.Employees.get_entities()
    smith_employees_request = smith_employees_request.filter(sef.and_(
                                                             smith_employees_request.FirstName == 'Jonh',
                                                             smith_employees_request.LastName == 'Smith'))
    for smith in smith_employees_request.execute():
        print(smith.EmployeeID)


Get a count of entities
-----------------------

Print a count of all employees:

.. code-block:: python

    count = northwind.entity_sets.Employees.get_entities().count().execute()
    print(count)


Get a count of entities via navigation property
-----------------------------------------------

Print a count of all orders associated with Employee 1:

.. code-block:: python

    count = northwind.entity_sets.Employees.get_entity(1).nav('Orders').get_entities().count().execute()
    print(count)
