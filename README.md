# python-pyodata

Enterprise-ready Python OData client which provides comfortable Python agnostic
way for communication with OData services.

The goal of this Python module is to hide all OData protocol implementation
details.

## Requirements

- [Python >= 3.6](https://www.python.org/downloads/release/python-368/)
- [requests == 2.20.0](https://pypi.org/project/requests/2.20.0/)
- [enum34 >= 1.0.4](https://pypi.org/project/enum34/)
- [funcsigs >= 1.0.2](https://pypi.org/project/funcsigs/)
- [lxml >= 3.7.3](https://pypi.org/project/lxml/)

## Download and Installation

You can obtain the latest version for this repository as [ZIP archive](https://github.com/SAP/python-pyodata/archive/master/pyodata.zip).

You can also use [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) to clone and pull the repository.

```bash
git clone https://github.com/SAP/python-pyodata.git
```

To make the pyodata Python module available in your projects, you need to
install the sub-directory __pyodata__ into [the Module Search Path](https://docs.python.org/3/tutorial/modules.html#the-module-search-path).

You can make use of [pip](https://packaging.python.org/tutorials/installing-packages/#installing-from-vcs)
to install the pyodata module automatically:

```bash
pip install -e git+https://github.com/SAP/python-pyodata.git
```

## Configuration

You can start building your OData projects straight away after installing the
Python module without any additional configuration steps needed.

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


### Property has this label

```python

assert client.schema.entity_type('Customer').proprty('CustomerID').label == 'Identifier'
```

### Property has a value helper

```python

assert client.schema.entity_type('Customer').proprty('City').value_helper is not None
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
* Run `python -m pytest` or `make check`
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

## Tips & tricks

If you want to avoid creating pull requests that fail on lint errors but you
always forgot to run `make check`, create the pre-commit file in the director
.git/hooks with the following content:

```bash
#!/bin/sh

make check
```

Do not forget to run `chmod +x .git/hooks/pre-commit` to make the hook script
executable.
