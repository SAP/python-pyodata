PYTHON_MODULE=pyodata
PYTHON_BINARIES=
PYTHON_MODULE_FILES=$(shell find $(PYTHON_MODULE) -type f -name '*.py')

TESTS_DIR=tests
TESTS_UNIT_DIR=$(TESTS_DIR)
TESTS_UNIT_FILES=$(shell find $(TESTS_UNIT_DIR) -type f -name '*.py')

PYTHON_BIN=python3

PYTEST_MODULE=pytest
PYTEST_PARAMS=--cov-report term --cov=pyodata

PYLINT_BIN=pylint
PYLINT_RC_FILE=.pylintrc
PYLINT_PARAMS=--output-format=parseable --reports=no

FLAKE8_BIN=flake8
FLAKE8_CONFIG_FILE=.flake8
FLAKE8_PARAMS=

COVERAGE_BIN=coverage3
COVERAGE_REPORT_ARGS=--skip-covered
COVERAGE_CMD_REPORT=$(COVERAGE_BIN) report
COVERAGE_CMD_HTML=$(COVERAGE_BIN) html
COVERAGE_HTML_DIR=.htmlcov
COVERAGE_HTML_ARGS=$(COVERAGE_REPORT_ARGS) -d $(COVERAGE_HTML_DIR)
COVERAGE_REPORT_FILES=$(PYTHON_BINARIES) $(PYTHON_MODULE_FILES)

all: check

.PHONY=check
lint: doc
	$(PYLINT_BIN) --rcfile=$(PYLINT_RC_FILE) $(PYLINT_PARAMS) $(PYTHON_MODULE)
	$(FLAKE8_BIN) --config=$(FLAKE8_CONFIG_FILE) $(FLAKE8_PARAMS) $(PYTHON_MODULE)

.PHONY=test
test:
	$(PYTHON_BIN) -m $(PYTEST_MODULE) $(PYTEST_PARAMS)

.coverage: $(COVERAGE_REPORT_FILES) $(TESTS_UNIT_FILES)
	$(MAKE) test PYTEST_PARAMS="--cov-report= --cov=$(PYTHON_MODULE)"

.PHONY: report-coverage
report-coverage: .coverage
	@ echo "Generating code coverage report ..."
	@ $(COVERAGE_CMD_REPORT) $(COVERAGE_REPORT_ARGS) $(COVERAGE_REPORT_FILES)

.PHONY: report-coverage-html
report-coverage-html: .coverage
	@ echo "Generating HTML code coverage report ..."
	@ $(COVERAGE_CMD_HTML) $(COVERAGE_HTML_ARGS) $(COVERAGE_REPORT_FILES)
	@ echo "Report: file://$$(pwd)/$(COVERAGE_HTML_DIR)/index.html"

.PHONY=check
check: lint test

.PHONY=doc
doc:
	$(MAKE) -C docs html
	@ echo -e "\nOpen: file://$$(pwd)/docs/_build/html/index.html"

.PHONY=clean
clean:
	rm --preserve-root -rf $(COVERAGE_HTML_DIR) .coverage
