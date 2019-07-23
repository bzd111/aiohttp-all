setup:
	pipenv shell
	pipenv install

PY = $(shell find code -type f -name "*.py")

lint:
	isort --check -rc code
	black --check code
	flake8 code
	mypy $(PY)

doc:
	make -C docs html
	@echo "open file://`pwd`/docs/_build/html/index.html"

fmt format:
	isort -rc code
	black code

test:
	pytest code/10-testing/tests


vtest:
	pytest -vvv code/10-testing/tests
