![Build Status](https://github.com/SAP/python-pyodata/actions/workflows/python-tests-compatibility.yml/badge.svg)
![Lint Status](https://github.com/SAP/python-pyodata/actions/workflows/python-linters.yml/badge.svg)
[![PyPI version](https://badge.fury.io/py/pyodata.svg)](https://badge.fury.io/py/pyodata)
[![codecov](https://codecov.io/gh/SAP/python-pyodata/branch/master/graph/badge.svg)](https://codecov.io/gh/SAP/python-pyodata)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/SAP/python-pyodata.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/SAP/python-pyodata/alerts/)
[![REUSE status](https://api.reuse.software/badge/github.com/SAP/python-pyodata)](https://api.reuse.software/info/github.com/SAP/python-pyodata)

# Python OData Client - pyodata

Python OData client which provides comfortable Python agnostic
way for communication with OData services.

The goal of this Python module is to hide all OData protocol implementation
details.

## Supported features

- OData V2

## Requirements

- [Python >= 3.7](https://www.python.org/downloads/)

## Download and Installation

Install and update using pip:

```bash
pip install -U pyodata
```

## Configuration

You can start building your OData projects straight away after installing the
Python module without any additional configuration steps needed.

## Limitations

There have been no limitations discovered yet.

## Known Issues

There are no known issues at this time.

## How to obtain support

We accept bug reports, feature requests, questions and comments via [GitHub issues](https://github.com/SAP/python-pyodata/issues)

## Usage

The only thing you need to do is to import the _pyodata_ Python module and
provide an object implementing interface compatible with [Session Object](https://2.python-requests.org/en/master/user/advanced/#session-objects)
for the library [Requests](https://2.python-requests.org/en/master/).

```python
import requests
import pyodata

SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

# Create instance of OData client
client = pyodata.Client(SERVICE_URL, requests.Session())
```

Find more sophisticated examples in [The User Guide](docs/usage/README.md).

## Contributing

Please, go through [the Contributing guideline](CONTRIBUTING.md).

### Authoring a patch

Here's an example workflow for a project `PyOData` hosted on Github
Your username is `yourname` and you're submitting a basic bugfix or feature.

* Hit 'fork' on Github, creating e.g. `yourname/PyOData`.
* `git clone git@github.com:yourname/PyOData`
* `git checkout -b foo_the_bars` to create new local branch named foo_the_bars
* Hack, hack, hack
* Run `python3 -m pytest` or `make check`
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

## License

Copyright (c) 2019 SAP SE or an SAP affiliate company. All rights reserved.
This file is licensed under the Apache Software License, v. 2 except as noted
otherwise in [the LICENSE file](LICENSE)
