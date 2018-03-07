# PyOData - Enterprise ready Python OData client

OData client Python module

## Requirements

- Python 2.7

## Usage

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

# Contributing

Before contributing, please, make yourself familiar with git. You can [try git
online](https://try.github.io/). Things would be easier for all of us if you do
your changes on a branch. Use a single commit for every logical reviewable
change, without unrelated modifications (that will help us if need to revert a
particular commit). Please avoid adding commits fixing your previous
commits, do amend or rebase instead.

Every commit must have either comprehensive commit message saying what is being
changed and why or a link (an issue number on Github) to a bug report where
this information is available. It is also useful to include notes about
negative decisions - i.e. why you decided to not do particular things. Please
bare in mind that other developers might not understand what the original
problem was.

## Full example

Here's an example workflow for a project `PyOData` hosted on Github
Your username is `yourname` and you're submitting a basic bugfix or feature.

* Hit 'fork' on Github, creating e.g. `yourname/PyOData`.
* `git clone git@github.com:yourname/PyOData`
* `git checkout -b foo_the_bars` to create new local branch named foo_the_bars
* Hack, hack, hack
* Run `python -m pytest`
* `git status`
* `git add`
* `git commit -s -m "Foo the bars"`
* `git push -u origin HEAD` to create foo_the_bars branch in your fork
* Visit your fork at Github and click handy "Pull request" button.
* In the description field, write down issue number (if submitting code fixing
  an existing issue) or describe the issue + your fix (if submitting a wholly
  new bugfix).
* Hit 'submit'! And please be patient - the maintainers will get to you when
  they can.
