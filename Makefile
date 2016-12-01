.PHONY: ship

ship:
	python setup.py sdist bdist_wheel
	twine upload dist/* --skip-existing
