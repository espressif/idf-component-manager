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


def get_idf_version(idf_py_path):
    idf_version = os.getenv('IDF_VERSION')
    if idf_version:
        return idf_version

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


class IDFSource(BaseSource):
    NAME = 'idf'

    def __init__(self, source_details):
        super(IDFSource, self).__init__(source_details=source_details)

        try:
            self.idf_path = os.environ['IDF_PATH']
        except KeyError:
            raise FetchingError('Please set IDF_PATH environment variable with a valid path to ESP-IDF')

    @staticmethod
    def is_me(name, details):
        return name == 'idf'

    @property
    def hash_key(self):
        return str(self.idf_path)

    @property
    def meta(self):
        return True

    def normalized_name(self, name):  # type: (str) -> str
        return self.NAME

    def versions(self, name, details=None, spec='*'):
        local_idf_version = get_idf_version(os.path.join(self.idf_path, 'tools', 'idf.py'))

        if semantic_version.match(spec, local_idf_version):
            versions = [HashedComponentVersion(local_idf_version)]
        else:
            versions = []

        return ComponentWithVersions(name=name, versions=versions)

    def download(self, component, download_path):
        if 'IDF_PATH' not in os.environ:
            FetchingError('Please set IDF_PATH environment variable with a valid path to ESP-IDF')

        return []

    def serialize(self):  # type: () -> Dict
        return {'type': self.name}
