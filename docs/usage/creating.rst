Creating
========

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
