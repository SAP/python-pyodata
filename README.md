[![Build Status](https://travis-ci.org/SAP/python-pyodata.svg?branch=master)](https://travis-ci.org/SAP/python-pyodata)

# Python OData Client - pyodata

Python OData client which provides comfortable Python agnostic
way for communication with OData services.

The goal of this Python module is to hide all OData protocol implementation
details.

## Requirements

- [Python >= 3.6](https://www.python.org/downloads/release/python-368/)

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

The only thing you need to do is to import the _pyodata_ Python module.

```python
import requests
import pyodata

SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

# Create instance of OData client
client = pyodata.Client(SERVICE_URL, requests.Session())
```

Find more sophisticated examples in the [USAGE](USAGE.md) section.

## Contributing

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

### Full example

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

## License

Copyright (c) 2019 SAP SE or an SAP affiliate company. All rights reserved.
This file is licensed under the Apache Software License, v. 2 except as noted
otherwise in [the LICENSE file](LICENSE)
