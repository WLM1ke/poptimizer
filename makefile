PKG_MNG=brew
TOOLS=python@3.10 poetry mongodb-community mongodb-database-tools
SRC=poptimizer
VENV_NAME=.venv
VENV_ACTIVATE=. ${VENV_NAME}/bin/activate
PYTHON=${VENV_NAME}/bin/python3

new:
	$(PKG_MNG) tap mongodb/brew
	$(PKG_MNG) install $(TOOLS)
	make venv
venv:
	rm -rf $(VENV_NAME)
	python3 -m venv $(VENV_NAME)
	make update
	pyppeteer-install
update:
	$(PKG_MNG) upgrade $(TOOLS)
	poetry env use $(PYTHON)
	poetry update
db_recover:
	@echo "Recover MongoDB"
	mongod --dbpath ./db --repair --directoryperdb
db_stop:
	@echo "Stop MongoDB"
	pkill -x mongod
lint:
	$(VENV_ACTIVATE);mypy $(SRC) && flake8 $(SRC)
test:
	$(VENV_ACTIVATE);pytest $(SRC) -v --cov=$(SRC) --cov-report=term-missing --cov-report=xml --setup-show
run:
	$(VENV_ACTIVATE);$(PYTHON) -m $(SRC)
