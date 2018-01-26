# PyOData - Enterprise ready Python OData client

OData client Python module

## Requirements

- Python 2.7

## Usage

```python
import requests
import pyodata

SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

# Create instance of OData client 
client = pyodata.Client(SERVICE_URL, requests.Session())

# Get employee identified by 1 and print employee first name
employee1 = client.entity_sets.Employees.get_entity(1).execute()
print employee1.FirstName

# Print unique identification (Id) and last name of all cemployees
employees = client.entity_sets.Employees.get_entities().select('EmployeeID,LasttName').execute()
    for employee in employees:
        print(employee.EmployeeID, employee.LastName)
```

# Batch requests 

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
