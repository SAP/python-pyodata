# Copyright 2018 SAP SE.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http: //www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from os.path import dirname, join
import os
import re
from setuptools import setup, find_packages
import subprocess

version_re = re.compile('^Version: (.+)$', re.M)
source_location = os.path.abspath(os.path.dirname(__file__))

def get_version():
    d = dirname(__file__)

    # Get the version using "git describe".
    cmd = 'git describe --tags --always'.split()
    try:
        version = subprocess.check_output(cmd).decode().strip()
    except subprocess.CalledProcessError:
        print('Unable to get version number from git tags, asuming inside package')
        # no git - we are inside pip package
        with open(join(d, 'PKG-INFO')) as f:
            version = version_re.search(f.read()).group(1)

    # PEP 386 compatibility
    if '-' in version:
        version = '.post'.join(version.split('-')[:2])
    return version

setup(
    name="pyodata",
    version=get_version(),
    license="Apache License Version 2.0",
    url="https://github.wdf.sap.corp/I335255/PyOData",
    author="Jakub Filak, Michal Nezerka, Patrik Petrik, Lubos Mjachky",
    author_email="jakub.filak@sap.com, michal.nezerka@sap.com, patrik.petrik@sap.com, lubos.mjachky@sap.com",
    description="Enterprise ready Python OData client",
    packages=find_packages(exclude=("tests")),
    zip_safe=False,
    install_requires=[
        "enum34>=1.0.4",
        "lxml==3.7.3",
    ],
    extras_require={
    },
    tests_require=[
        "setuptools>=38.2.4",
        "setuptools-scm>=1.15.6",
        "funcsigs>=1.0.2",
        "requests==2.13.0",
        "responses>=0.8.1",
        "pytest>=2.7.0",
    ],
    classifiers=[ # cf. http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    entry_points = {
    },
)
