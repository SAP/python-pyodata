PYTHON_MODULE=pyodata

PYTHON_BIN=python3

PYTEST_MODULE=pytest
PYTEST_PARAMS=--cov-report term --cov=./pyodata/v2

PYLINT_BIN=pylint
PYLINT_RC_FILE=.pylintrc
PYLINT_PARAMS=--output-format=parseable --reports=no

FLAKE8_BIN=flake8
FLAKE8_CONFIG_FILE=.flake8
FLAKE8_PARAMS=

all: check

.PHONY=check
lint: doc
	$(PYLINT_BIN) --rcfile=$(PYLINT_RC_FILE) $(PYLINT_PARAMS) $(PYTHON_MODULE)
	$(FLAKE8_BIN) --config=$(FLAKE8_CONFIG_FILE) $(FLAKE8_PARAMS) $(PYTHON_MODULE)

.PHONY=test
test:
	$(PYTHON_BIN) -m $(PYTEST_MODULE) $(PYTEST_PARAMS)

.PHONY=check
check: lint test

.PHONY=doc
doc:
	$(MAKE) -C docs html
	@ echo -e "\nOpen: file://$$(pwd)/docs/_build/html/index.html"
