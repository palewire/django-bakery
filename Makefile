.PHONY: test ship

test:
	flake8 bakery
	python setup.py test

ship:
	python setup.py sdist bdist_wheel
	twine upload dist/* --skip-existing
