.PHONY: test ship build

test:
	flake8 bakery
	python setup.py test

ship:
	python setup.py sdist bdist_wheel
	twine upload dist/* --skip-existing

build:
	clear
	python example/manage.py build --verbosity=3
