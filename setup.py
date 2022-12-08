# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import io
import os

import setuptools

AUTHOR = 'Sergei Silnov'
MAINTAINER = 'Sergei Silnov'
EMAIL = 'sergei.silnov@espressif.com'

NAME = 'idf_component_manager'
SHORT_DESCRIPTION = 'The component manager for ESP-IDF'
LICENSE = 'Apache License 2.0'
URL = 'https://github.com/espressif/idf-component-manager'
REQUIRES = [
    'cachecontrol[filecache]<=0.12.6;python_version<"3.6"',
    'cachecontrol[filecache]>0.12.6;python_version>="3.6"',
    'cffi<1.15;python_version<"3.6"',
    'click<8.0;python_version<"3"',
    'click==7.0;python_version=="3.4.*"',
    'click<8.0.0;python_version=="3.5.*"',
    'click<8.1.0;python_version=="3.6.*"',
    'click;python_version>="3.7"',
    'colorama;python_version=="2.7.*"',
    'colorama;python_version>="3.5"',
    'contextlib2<=0.6.0;python_version<"3.6"',
    'contextlib2>0.6.0;python_version>="3.6"',
    'future',
    'packaging',
    'pathlib;python_version<"3.4"',
    'pyyaml<=5.2;python_version=="3.4.*"',
    'pyyaml>5.2;python_version>="3.5"',
    'pyyaml<=5.2;python_version=="2.7.*"',
    'requests<3',
    'requests-file',
    'requests-toolbelt',
    'schema',
    'six',
    'tqdm<5',
]

info = {}  # type: ignore
path = os.path.abspath(os.path.dirname(__file__))

with io.open('README.md', mode='r', encoding='utf-8') as readme:
    LONG_DESCRIPTION = readme.read()

with io.open(os.path.join(path, 'idf_component_tools', '__version__.py'), mode='r', encoding='utf-8') as f:
    exec(f.read(), info)  # nosec

setuptools.setup(
    name=NAME,
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    license=LICENSE,
    version=info['__version__'],
    author=AUTHOR,
    maintainer=MAINTAINER,
    author_email=EMAIL,
    url=URL,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    packages=setuptools.find_packages(
        exclude=('*.tests', '*.tests.*', 'tests.*', 'tests', '*_tests', '*_tests_*', 'tests_*')),
    scripts=[],
    install_requires=REQUIRES,
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'compote = idf_component_manager.cli:safe_cli',
        ],
    },
)
