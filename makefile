PKG_MNG=brew
PYTHON_VER=python@3.10
TOOLS=${PYTHON_VER} poetry
SRC=poptimizer
VENV_NAME=.venv
VENV_ACTIVATE=. ${VENV_NAME}/bin/activate
PYTHON=${VENV_NAME}/bin/python3

new:
	$(PKG_MNG) install $(TOOLS)
	$(PKG_MNG) unlink python
	$(PKG_MNG) link $(PYTHON_VER)
	make venv
venv:
	rm -rf $(VENV_NAME)
	python3 -m venv $(VENV_NAME)
	make update
update:
	$(PKG_MNG) upgrade $(TOOLS)
	poetry env use $(PYTHON)
	poetry update
lint:
	$(VENV_ACTIVATE);black $(SRC) && mypy $(SRC) && flake8 $(SRC)
test: lint
	$(VENV_ACTIVATE);pytest $(SRC) -v --cov=$(SRC) --cov-report=term-missing --cov-report=xml --setup-show
run:
	$(VENV_ACTIVATE);(export $$(cat .env | grep -o '^[^#]\+' | xargs) && $(PYTHON) -m $(SRC))