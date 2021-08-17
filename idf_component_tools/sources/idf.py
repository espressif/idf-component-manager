import os
import re
import subprocess  # nosec
import sys

import semantic_version

from ..errors import FetchingError
from ..manifest import ComponentWithVersions, HashedComponentVersion
from .base import BaseSource

try:
    from typing import Dict
except ImportError:
    pass

IDF_VERSION_REGEX = re.compile(r'v(\d\.\d(?:\.\d)?)')


def get_idf_version():
    idf_version = os.getenv('IDF_VERSION')
    if idf_version:
        return idf_version

    idf_py_path = os.path.join(get_idf_path(), 'tools', 'idf.py')
    try:
        idf_version = subprocess.check_output([sys.executable, idf_py_path, '--version'])  # nosec
    except subprocess.CalledProcessError:
        raise FetchingError(
            'Could not get IDF version from calling "idf.py --version".\n'
            'idf.py path: {}'.format(idf_py_path))
    else:
        try:
            string_type = basestring  # type: ignore
        except NameError:
            string_type = str

        if not isinstance(idf_version, string_type):
            idf_version = idf_version.decode('utf-8')

    res = IDF_VERSION_REGEX.findall(idf_version)
    if len(res) == 1:
        return str(semantic_version.Version.coerce(res[0]))
    else:
        raise FetchingError(
            'Could not parse IDF version from calling "idf.py --version".\n'
            'Output: {}'.format(idf_version))


def get_idf_path():  # type: () -> str
    try:
        return os.environ['IDF_PATH']
    except KeyError:
        raise FetchingError('Please set IDF_PATH environment variable with a valid path to ESP-IDF')


class IDFSource(BaseSource):
    NAME = 'idf'

    @staticmethod
    def is_me(name, details):
        return name == IDFSource.NAME

    @property
    def hash_key(self):
        return self.NAME

    @property
    def meta(self):
        return True

    def normalized_name(self, name):  # type: (str) -> str
        return self.NAME

    def versions(self, name, details=None, spec='*', target=None):
        local_idf_version = get_idf_version()

        if semantic_version.match(spec, local_idf_version):
            versions = [HashedComponentVersion(local_idf_version)]
        else:
            versions = []

        return ComponentWithVersions(name=name, versions=versions)

    def download(self, component, download_path):
        get_idf_path()
        return []

    def serialize(self):  # type: () -> Dict
        return {'type': self.name}
