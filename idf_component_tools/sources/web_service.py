"""Component source that downloads components from web service"""

import os
import re
import shutil
import tempfile
from hashlib import sha256
from io import open

import requests

import idf_component_tools.api_client as api_client

from ..archive_tools import ArchiveError, get_format_from_path, unpack_archive
from ..errors import FetchingError
from .base import BaseSource

try:
    from urllib.parse import urlparse  # type: ignore
except ImportError:
    from urlparse import urlparse  # type: ignore

try:
    from typing import Dict
except ImportError:
    pass


def default_component_service_url():
    return os.getenv('DEFAULT_COMPONENT_SERVICE_URL', 'https://api.components.espressif.com/')


DEFAULT_NAMESPACE = 'espressif'


class WebServiceSource(BaseSource):
    NAME = 'service'

    def __init__(self, source_details=None):
        super(WebServiceSource, self).__init__(source_details=source_details)
        self.base_url = str(self.source_details.get('service_url', default_component_service_url()))
        self.api_client = self.source_details.get(
            'api_client', api_client.APIClient(base_url=self.base_url, source=self))

    @classmethod
    def required_keys(cls):
        return ['service_url']

    @property
    def hash_key(self):
        if self._hash_key is None:
            url = urlparse(self.base_url)
            netloc = url.netloc
            path = '/'.join(filter(None, url.path.split('/')))
            normalized_path = '/'.join([netloc, path])
            self._hash_key = sha256(normalized_path.encode('utf-8')).hexdigest()
        return self._hash_key

    @staticmethod
    def is_me(name, details):
        # This should be run last
        return True

    def versions(self, name, details=None, spec='*'):
        cmp_with_versions = self.api_client.versions(name, spec)

        if not cmp_with_versions:
            raise FetchingError('Cannot get versions of "%s"' % name)

        return cmp_with_versions

    def unique_path(self, name, version):  # type: (str, str) -> str
        """Unique identifier for cache"""
        return '~'.join([name.replace('/', '~~'), str(version), self.hash_key])

    @property
    def component_hash_required(self):  # type: () -> bool
        return True

    @property
    def downloadable(self):  # type: () -> bool
        return True

    def normalized_name(self, name):
        if '/' not in name:
            name = '/'.join([DEFAULT_NAMESPACE, name])

        return name

    def download(self, component, download_path):
        # Check for required components

        if not component.component_hash:
            raise FetchingError('Component hash is required for componets from web service')

        if not component.version:
            raise FetchingError('Version should provided for %s' % component.name)

        component = self.api_client.component(component.name, component.version)
        url = component.download_url

        if not url:
            raise FetchingError(
                'Unexpected response: URL wasn\'t found for version %s of "%s"',
                component.version,
                component.name,
            )

        with requests.get(url, stream=True, allow_redirects=True) as r:

            # Trying to get extension from url
            original_filename = url.split('/')[-1]

            try:
                extension = get_format_from_path(original_filename)[1]
            except ArchiveError:
                extension = None

            if r.status_code != 200:
                raise FetchingError(
                    'Cannot download component %s@%s. Server returned HTTP code %s' %
                    (component.name, component.version, r.status_code))

            # If didn't find anything useful, trying content disposition
            content_disposition = r.headers.get('content-disposition')
            if not extension and content_disposition:
                filenames = re.findall('filename=(.+)', content_disposition)
                try:
                    extension = get_format_from_path(filenames[0])[1]
                except IndexError:
                    raise FetchingError('Web Service returned invalid download url')

            tempdir = tempfile.mkdtemp()

            try:
                unique_path = self.unique_path(component.name, component.version)
                filename = '%s.%s' % (unique_path, extension)
                file_path = os.path.join(tempdir, filename)

                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)

                unpack_archive(file_path, download_path)
            finally:
                shutil.rmtree(tempdir)

        return [download_path]

    @property
    def service_url(self):
        return self.base_url

    def serialize(self):  # type: () -> Dict
        return {
            'service_url': self.base_url,
            'type': self.name,
        }
