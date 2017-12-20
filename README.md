# PyOData - Enterprise ready Python OData client

OData client Python module

## Requirements

- Python 2.7

## Usage

```python
import requests
import pyodata

SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

# Create instance of OData consumer
client = pyodata.Client(SERVICE_URL, requests.Session())

employee1 = client.entity_sets.Employees.get_entity(1)
print employee1.FirstName
```
