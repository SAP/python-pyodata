# Usage examples

### Get the service

```python
import requests
import pyodata

SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

# Create instance of OData client
client = pyodata.Client(SERVICE_URL, requests.Session())
```

### Get one entity identified by its key value

```python
# Get employee identified by 1 and print employee first name
employee1 = client.entity_sets.Employees.get_entity(1).execute()
print employee1.FirstName
```

### Get one entity identified by its key value which is not scalar

```python
# Get number of orderd units in the order identified by ProductID 42 and OrderID 10248.
order = client.entity_sets.Order_Details.get_entity(OrderID=10248, ProductID=42).execute()
print(order.Quantity)
```

### Get all entities of an entity set

```python

# Print unique identification (Id) and last name of all cemployees
employees = client.entity_sets.Employees.get_entities().select('EmployeeID,LasttName').execute()
for employee in employees:
    print(employee.EmployeeID, employee.LastName)
```

### Get entities matching a filter

```python
# Print unique identification (Id) of all employees with name John Smith
smith_employees_request = client.entity_sets.Employees.get_entities()
smith_employees_request = smith_employees_request.filter("FirstName eq 'John' and LastName eq 'Smith'")
for smith in smith_employees.execute():
    print(smith.EmployeeID)
```

### Get entities matching a filter in more Pythonic way

```python
from pyodata.v2.service import GetEntitySetFilter

# Print unique identification (Id) of all employees with name John Smith
smith_employees_request = client.entity_sets.Employees.get_entities()
smith_employees_request = smith_employees_request.filter(GetEntitySetFilter.and_(
                                                         smith_employees_request.FirstName == 'Jonh',
                                                         smith_employees_request.LastName == 'Smith'))
for smith in smith_employees_request.execute():
    print(smith.EmployeeID)
```

### Creating entity

You need to use the method set which accepts key value parameters:

```python
employee_data = {
    'FirstName': 'Mark',
    'LastName': 'Goody',
    'Address': {
        'HouseNumber': 42,
        'Street': 'Paradise',
        'City': 'Heaven'
    }
}

create_request = client.entity_sets.Employees.create_entity()
create_request.set(**employee_data)

new_employee_entity = create_request.execute()
```

or you can do it explicitly:

```python
create_request = client.entity_sets.Employees.create_entity()
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
```


### Batch requests

Example of batch request that contains 3 simple entity queries
```
client = pyodata.Client(SERVICE_URL, requests.Session())

batch = client.create_batch()

batch.add_request(client.entity_sets.Employees.get_entity(108))
batch.add_request(client.entity_sets.Employees.get_entity(234))
batch.add_request(client.entity_sets.Employees.get_entity(23))

response = batch.execute()

print(response[0].EmployeeID, response[0].LastName)
print(response[1].EmployeeID, response[1].LastName)
print(response[1].EmployeeID, response[1].LastName)
```

Example of batch request that contains simple entity query as well
as changest consisting of two requests for entity modification
```
client = pyodata.Client(SERVICE_URL, requests.Session())

batch = client.create_batch()

batch.add_request(client.entity_sets.Employees.get_entity(108))

changeset = client.create_changeset()

changeset.add_request(client.entity_sets.Employees.update_entity(45).set(LastName='Douglas'))

batch.add_request(changeset)

response = batch.execute()

print(response[0].EmployeeID, response[0].LastName)
```

### Calling a function import

```python
products = client.functions.GetProductsByRating.parameter('rating', 16).execute()
for prod in products:
    print(prod)
```

## Error handling

PyOData returns HttpError when the response code does not match the expected
code.

In the case you know the implementation of back-end part and you want to show
accurate errors reported by your service, you can replace HttpError by your
sub-class HttpError by assigning your type into the class member VendorType of
the class HttpError.

```python
from pyodata.exceptions import HttpError


class MyHttpError(HttpError):

    def __init__(self, message, response):
        super(MyHttpError, self).__init__('Better message', response)


HttpError.VendorType = MyHttpError
```

The class ```pyodata.vendor.SAP.BusinessGatewayError``` is an example of such
an HTTP error handling.

## Metadata tests

By default, the client makes sure that references to properties, entities and
entity sets are pointing to existing elements.

The most often problem that we had to deal with was an invalid ValueList annotion
pointing to a non-existing property.

To enable verification of service definition, the client instance of the class
`Service` publishes the property `schema` which returns an instance of the
class `Schema` from the module [pyodata.v2.model](pyodata/v2/model.py) and it
contains parsed `$metadata`.

### List of the defined EntitySets

If you need to iterate over all EntitySets:

```python
for es in service.schema.entity_sets:
     print(es.name)
```

or if you just need the list of EntitySet names:

```python
entity_set_names = [es.name for es in service.schema.entity_sets]
```

### Property has this label

```python

assert client.schema.entity_type('Customer').proprty('CustomerID').label == 'Identifier'
```

### Property has a value helper

```python

assert client.schema.entity_type('Customer').proprty('City').value_helper is not None
```

