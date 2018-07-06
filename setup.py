import os
from setuptools import setup

with open('VERSION', 'r') as f:
    version = f.readline().strip()


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='nptool',
    version=version,
    packages=['nptool'],
    install_requires=[
        'click',
        'cityhash',
        'jsonschema',
        'structlog',
        'python-dateutil',
        'colorama',
        'pytz',
        'bel',
    ],
    entry_points={
        'console_scripts': [
            'nptool = nptool.nptool:main'
        ]
    },
    description=read('README.md'),
    author="William Hayes",
    author_email="whayes@biodati.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.6",
    ],
)
