# PyOData - Enterprise ready Python OData client

OData client Python module

## Requirements

- Python 2.7

## Usage

```python
import requests

import pyodata.v2.model
import pyodata.v2.service

service_url = 'http://services.odata.org/V3/Northwind/Northwind.svc/'
metadata = requests.get(service_url + '$metadata').content
schema = pyodata.v2.model.schema_from_xml(metadata)
service = pyodata.v2.service.Service(service_url, schema, requests)

employee1 = service.entity_sets.Employees.get_entity(1)
print employee1.FirstName
```
