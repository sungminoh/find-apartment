#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
from itertools import chain

from setuptools import find_packages, setup


NAME = 'find_apartment'
DESCRIPTION = 'Get yelp reviews from apartmnet.com search result page'
URL = 'https://github.com/sungminoh/find-apartment'
EMAIL = 'smoh2044@gmail.com'
AUTHOR = 'Sungmin Oh'
REQUIRES_PYTHON = '>=3.6.0'
VERSION = '0.1.0'

# What packages are required for this module to be executed?
REQUIRED = [
    'wheel',
    'bs4',
    'requests',
    'selenium',
]

# What packages are optional?
EXTRAS_REQUIRED = {
    'dev': ['neovim', 'ptipython', 'pudb', 'ipdb'],
}

here = os.path.abspath(os.path.dirname(__file__))

try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

about = {'__version__': VERSION}

setup(
    name=NAME,
    version=about['__version__'],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(
        exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    install_requires=REQUIRED,
    extras_require={
        **EXTRAS_REQUIRED,
        'all': list(chain(*EXTRAS_REQUIRED.values())),
    },
    entry_points={'console_scripts': ['find_apartment=find_apartment.housing:main']},
)
