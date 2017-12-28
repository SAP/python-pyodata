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
