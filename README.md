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

## Limitations

There have been no limitations discovered yet.

## Known Issues

This projects is issue-free. Should you have any doubts, please, consult [our issue tracker](https://github.com/SAP/python-pyodata/issues).

## How to obtain support

We provide unclaimable support via [GitHub issues](https://github.com/SAP/python-pyodata/issues)

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

# License

Copyright (c) 2019 SAP SE or an SAP affiliate company.

All rights reserved.  This file is licensed under

    the Apache Software License, v. 2

except as noted otherwise in [the LICENSE file](LICENSE)
