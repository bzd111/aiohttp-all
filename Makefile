setup:
	pipenv shell
	pipenv install

PY = $(shell find . -type f -name "*.py")

lint:
	isort --check -rc .
	black --check .
	flake8 .
	mypy $(PY)

doc:
	make -C docs html
	@echo "open file://`pwd`/docs/_build/html/index.html"

fmt format:
	isort -rc .
	black .

test:
	pytest code/10-testing/tests


vtest:
	pytest -vvv code/10-testing/tests
