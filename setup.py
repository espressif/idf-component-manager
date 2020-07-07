import io
import os

import setuptools

with io.open('README.md', mode='r', encoding='utf-8') as fh:
    long_description = fh.read()

info = {}  # type: ignore
path = os.path.abspath(os.path.dirname(__file__))
with io.open(os.path.join(path, 'idf_component_manager', '__version__.py'), mode='r', encoding='utf-8') as f:
    exec(f.read(), info)  # nosec

setuptools.setup(
    name='idf_component_manager',
    version=info['__version__'],
    author='Sergei Silnov',
    author_email='sergei.silnov@espressif.com',
    description='Component Manager for ESP IDF',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://espressif.com',
    packages=setuptools.find_packages(exclude=('*.tests', '*.tests.*', 'tests.*', 'tests')),
    install_requires=[
        'future',
        'idf_component_tools',
        'semantic_version',
        'typing',
    ],
    include_package_data=True,
)
