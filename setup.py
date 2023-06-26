from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in excela/__init__.py
from excela import __version__ as version

setup(
	name="excela",
	version=version,
	description="excela",
	author="info@example.com",
	author_email="info@example.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
