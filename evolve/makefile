PKG_MNG=brew
TOOLS=python poetry
SRC=evolve
VENV_NAME=.venv
PYTHON=${VENV_NAME}/bin/python3

new:
	$(PKG_MNG) install $(TOOLS)
	make venv
venv:
	rm -rf $(VENV_NAME)
	python3 -m venv $(VENV_NAME)
	make update
update:
	$(PKG_MNG) upgrade $(TOOLS)
	poetry update
lint:
	mypy $(SRC) && flake8 $(SRC)
test: lint
	pytest $(SRC) -v --cov=poptimizer --cov-report=term-missing --cov-report=xml --setup-show
run:
	(export $$(cat .env | grep -o '^[^#]\+' | xargs) && $(PYTHON) -m $(SRC))