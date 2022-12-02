# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Component source that downloads components from web service"""

import os
import re
import shutil
import tempfile
from hashlib import sha256
from io import open

import requests

import idf_component_tools.api_client as api_client
from idf_component_tools.semver import SimpleSpec

from ..archive_tools import ArchiveError, get_format_from_path, unpack_archive
from ..config import component_registry_url
from ..constants import IDF_COMPONENT_REGISTRY_URL, IDF_COMPONENT_STORAGE_URL
from ..errors import FetchingError, hint
from ..file_tools import copy_directory
from ..hash_tools import validate_dir
from . import utils
from .base import BaseSource

try:
    from urllib.parse import urlparse  # type: ignore
except ImportError:
    from urlparse import urlparse  # type: ignore

try:
    from typing import TYPE_CHECKING, Dict

    if TYPE_CHECKING:
        from ..manifest import SolvedComponent
except ImportError:
    pass

CANONICAL_IDF_COMPONENT_REGISTRY_API_URL = 'https://api.components.espressif.com/'
IDF_COMPONENT_REGISTRY_API_URL = '{}api/'.format(IDF_COMPONENT_REGISTRY_URL)


def download_archive(url, download_dir):  # type: (str, str) -> str
    session = api_client.create_session(cache=False)

    try:
        with session.get(url, stream=True, allow_redirects=True) as r:
            # Trying to get extension from url
            original_filename = url.split('/')[-1]

            try:
                extension = get_format_from_path(original_filename)[1]
            except ArchiveError:
                extension = None

            if r.status_code != 200:
                raise FetchingError('Server returned HTTP code {}'.format(r.status_code))

            # If didn't find anything useful, trying content disposition
            content_disposition = r.headers.get('content-disposition')
            if not extension and content_disposition:
                filenames = re.findall('filename=(.+)', content_disposition)
                try:
                    extension = get_format_from_path(filenames[0])[1]
                except IndexError:
                    raise FetchingError('Web Service returned invalid download url')

            filename = 'component.%s' % extension
            file_path = os.path.join(download_dir, filename)

            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            return file_path
    except requests.exceptions.RequestException as e:
        raise FetchingError(str(e))


class WebServiceSource(BaseSource):
    NAME = 'service'

    def __init__(self, source_details=None, **kwargs):
        super(WebServiceSource, self).__init__(source_details=source_details, **kwargs)

        # Use URL from source details with the high priority
        self.base_url = self.source_details.get('service_url')

        # Use the default URL, even if the lock file was made with the canonical one
        if self.base_url == CANONICAL_IDF_COMPONENT_REGISTRY_API_URL:
            self.base_url = IDF_COMPONENT_REGISTRY_API_URL

        self.storage_url = self.source_details.get('storage_url')

        if not self.base_url and not self.storage_url:
            self.base_url, self.storage_url = component_registry_url()

        self.api_client = self.source_details.get('api_client')

        if self.api_client is None:
            self.api_client = api_client.APIClient(base_url=self.base_url, storage_url=self.storage_url, source=self)

        if not self.base_url and not self.storage_url:
            FetchingError('Cannot fetch a dependency with when registry is not defined')

        self.pre_release = self.source_details.get('pre_release')

    @classmethod
    def required_keys(cls):
        return {}

    @classmethod
    def optional_keys(cls):
        return {'pre_release': 'bool', 'storage_url': 'str', 'service_url': 'str'}

    @property
    def hash_key(self):
        if self._hash_key is None:
            url = urlparse(self.base_url or self.storage_url)
            netloc = url.netloc
            path = '/'.join(filter(None, url.path.split('/')))
            normalized_path = '/'.join([netloc, path])
            self._hash_key = sha256(normalized_path.encode('utf-8')).hexdigest()
        return self._hash_key

    @staticmethod
    def is_me(name, details):
        # This should be run last
        return True

    def component_cache_path(self, component):  # type: (SolvedComponent) -> str
        component_dir_name = '_'.join(
            [
                self.normalized_name(component.name).replace('/', '__'),
                str(component.version),
                str(component.component_hash)[:8],
            ])
        path = os.path.join(self.cache_path(), component_dir_name)
        return path

    def versions(self, name, details=None, spec='*', target=None):
        cmp_with_versions = self.api_client.versions(component_name=name, spec=spec)
        versions = []
        other_targets_versions = []
        pre_release_versions = []

        for version in cmp_with_versions.versions:
            if target and version.targets and target not in version.targets:
                other_targets_versions.append(version)
                continue

            if not self.pre_release and version.semver.prerelease and not SimpleSpec(spec).contains_prerelease:
                pre_release_versions.append(str(version))
                continue

            versions.append(version)

        cmp_with_versions.versions = versions
        if not versions:
            current_target = '"{}"'.format(target) if target else ''

            if pre_release_versions:
                hint(
                    'Component "{}" has some pre-release versions: "{}" satisfies your requirements. '
                    'To allow pre-release versions add "pre_release: true" '
                    'to the dependency in the manifest.'.format(name, '", "'.join(pre_release_versions)))

            if other_targets_versions:
                targets = {t for v in other_targets_versions for t in v.targets}
                hint(
                    'Component "{}" has suitable versions for other targets: "{}". '
                    'Is your current target {} set correctly?'.format(name, '", "'.join(targets), current_target))

            raise FetchingError(
                'Cannot find versions of "{}" with version satisfying "{}" '
                'for the current target {}'.format(name, spec, current_target))

        return cmp_with_versions

    @property
    def component_hash_required(self):  # type: () -> bool
        return True

    @property
    def downloadable(self):  # type: () -> bool
        return True

    def normalized_name(self, name):
        return utils.normalized_name(name)

    def download(self, component, download_path):  # type: (SolvedComponent, str) -> str
        # Check for required components
        if not component.component_hash:
            raise FetchingError('Component hash is required for componets from web service')

        if not component.version:
            raise FetchingError('Version should be provided for %s' % component.name)

        if self.up_to_date(component, download_path):
            return download_path

        # Check if component is in the cache
        if validate_dir(self.component_cache_path(component), component.component_hash):
            copy_directory(self.component_cache_path(component), download_path)
            return download_path

        component_manifest = self.api_client.component(component_name=component.name, version=component.version)
        url = component_manifest.download_url

        if not url:
            raise FetchingError(
                'Unexpected response: URL wasn\'t found for version %s of "%s"',
                component.version,
                component.name,
            )

        tempdir = tempfile.mkdtemp()

        try:
            file_path = download_archive(url, tempdir)
            unpack_archive(file_path, self.component_cache_path(component))
            copy_directory(self.component_cache_path(component), download_path)
        except FetchingError as e:
            raise FetchingError('Cannot download component {}@{}. {}'.format(component.name, component.version, str(e)))
        finally:
            shutil.rmtree(tempdir)

        return download_path

    @property
    def service_url(self):
        return self.base_url

    def serialize(self):  # type: () -> Dict
        source = {'type': self.name}

        service_url = self.base_url

        # Use canonical API url for lock file
        if service_url == IDF_COMPONENT_REGISTRY_API_URL:
            service_url = CANONICAL_IDF_COMPONENT_REGISTRY_API_URL

        if service_url is not None:
            source['service_url'] = service_url

        if self.storage_url != IDF_COMPONENT_STORAGE_URL and self.storage_url is not None:
            source['storage_url'] = self.storage_url

        if self.pre_release is not None:
            source['pre_release'] = self.pre_release

        return source
