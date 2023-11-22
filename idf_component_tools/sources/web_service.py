# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Component source that downloads components from web service"""

import os
import re
import shutil
import tempfile
from hashlib import sha256
from io import open

import requests

from idf_component_manager.service_details import (
    get_component_registry_url_with_profile,
    get_storage_urls,
)
from idf_component_tools.hash_tools.validate_managed_component import (
    validate_managed_component_by_manifest,
)
from idf_component_tools.registry.storage_client import StorageClient
from idf_component_tools.semver import SimpleSpec

from ..archive_tools import ArchiveError, get_format_from_path, unpack_archive
from ..constants import IDF_COMPONENT_REGISTRY_URL, IDF_COMPONENT_STORAGE_URL, UPDATE_SUGGESTION
from ..errors import FetchingError
from ..file_tools import copy_directory
from ..messages import hint
from ..registry.base_client import create_session
from . import utils
from .base import BaseSource
from .web_service_keys import WEB_SERVICE_OPTIONAL_KEYS, WEB_SERVICE_REQUIRED_KEYS

try:
    from urllib.parse import urlparse  # type: ignore
except ImportError:
    from urlparse import urlparse  # type: ignore

try:
    from typing import TYPE_CHECKING, Dict

    if TYPE_CHECKING:
        from ..manifest import ManifestManager
        from ..manifest.solved_component import SolvedComponent
except ImportError:
    pass

CANONICAL_IDF_COMPONENT_REGISTRY_API_URL = 'https://api.components.espressif.com/'
IDF_COMPONENT_REGISTRY_API_URL = '{}api/'.format(IDF_COMPONENT_REGISTRY_URL)


def download_archive(url, download_dir):  # type: (str, str) -> str
    session = create_session(cache=False)

    try:
        with session.get(url, stream=True, allow_redirects=True) as r:  # type: requests.Response
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
        self.__storage_url = self.source_details.get('storage_url')

        # Use the default URL, even if the lock file was made with the canonical one
        if self.base_url == CANONICAL_IDF_COMPONENT_REGISTRY_API_URL:
            self.base_url = IDF_COMPONENT_REGISTRY_API_URL

        if self.base_url == IDF_COMPONENT_REGISTRY_API_URL and not self.__storage_url:
            self.__storage_url = IDF_COMPONENT_STORAGE_URL

        self.__api_client = self.source_details.get('api_client')

        if not self.base_url and not self.__storage_url:
            FetchingError('Cannot fetch a dependency with when registry is not defined')

        self.pre_release = self.source_details.get('pre_release')

    @classmethod
    def required_keys(cls):
        return WEB_SERVICE_REQUIRED_KEYS

    @classmethod
    def optional_keys(cls):
        return WEB_SERVICE_OPTIONAL_KEYS

    @property
    def hash_key(self):
        if self._hash_key is None:
            url = urlparse(self.base_url or self._storage_url)
            netloc = url.netloc
            path = '/'.join(filter(None, url.path.split('/')))
            normalized_path = '/'.join([netloc, path])
            self._hash_key = sha256(normalized_path.encode('utf-8')).hexdigest()
        return self._hash_key

    @property
    def _storage_url(self):
        if self.base_url and not self.__storage_url:
            self.__storage_url = get_storage_urls(self.base_url)[0]
        return self.__storage_url

    @property
    def _api_client(self):
        if self.__api_client is None:
            self.__api_client = StorageClient(storage_url=self._storage_url, sources=[self])
        return self.__api_client

    @staticmethod
    def create_sources_if_valid(
        name, details, manifest_manager=None
    ):  # type: (str, dict, ManifestManager | None) -> list[BaseSource]
        # This should be run last
        if not details:
            details_copy = {}
        else:
            details_copy = details.copy()
        base_url = details_copy.get('service_url')

        # Use the default URL, even if the lock file was made with the canonical one
        if base_url == CANONICAL_IDF_COMPONENT_REGISTRY_API_URL:
            base_url = IDF_COMPONENT_REGISTRY_API_URL

        # Get storage_urls from details > from profile/env > from API
        storage_urls = details_copy.get('storage_url')

        if isinstance(storage_urls, str):
            storage_urls = [storage_urls]

        if not base_url and not storage_urls:
            base_url, storage_urls = get_component_registry_url_with_profile()
            details_copy['service_url'] = base_url

        # WebServiceSource will get storage_url from API when needed
        if not storage_urls:
            return [WebServiceSource(details_copy, manifest_manager=manifest_manager)]

        sources = []  # type: list[BaseSource]
        if storage_urls:
            for storage_url in storage_urls:
                details_copy['storage_url'] = storage_url
                sources.append(WebServiceSource(details_copy, manifest_manager=manifest_manager))

        return sources

    def component_cache_path(self, component):  # type: (SolvedComponent) -> str
        component_dir_name = '_'.join(
            [
                self.normalized_name(component.name).replace('/', '__'),
                str(component.version),
                str(component.component_hash)[:8],
            ]
        )
        path = os.path.join(self.cache_path(), component_dir_name)
        return path

    def versions(self, name, details=None, spec='*', target=None):
        cmp_with_versions = self._api_client.versions(component_name=name, spec=spec)
        versions = []
        other_targets_versions = []
        pre_release_versions = []
        newer_component_manager_versions = []

        for version in cmp_with_versions.versions:
            if target and version.targets and target not in version.targets:
                other_targets_versions.append(version)
                continue

            if (
                not self.pre_release
                and version.semver.prerelease
                and not SimpleSpec(spec).contains_prerelease
            ):
                pre_release_versions.append(str(version))
                continue

            if not version.all_build_keys_known:
                newer_component_manager_versions.append(str(version))
                continue

            versions.append(version)

        cmp_with_versions.versions = versions
        if not versions:
            current_target = '"{}"'.format(target) if target else ''

            if pre_release_versions:
                hint(
                    'Component "{}" has some pre-release versions: "{}" '
                    'satisfies your requirements. '
                    'To allow pre-release versions add "pre_release: true" '
                    'to the dependency in the manifest.'.format(
                        name, '", "'.join(pre_release_versions)
                    )
                )

            if other_targets_versions:
                targets = {t for v in other_targets_versions for t in v.targets}
                hint(
                    'Component "{}" has suitable versions for other targets: "{}". '
                    'Is your current target {} set correctly?'.format(
                        name, '", "'.join(targets), current_target
                    )
                )

            if newer_component_manager_versions:
                hint(
                    'Component "{}" has versions "{}" '
                    'that support only newer version of idf-component-manager '
                    'that satisfy your requirements.\n'
                    '{}'.format(
                        name, '", "'.join(newer_component_manager_versions), UPDATE_SUGGESTION
                    )
                )

            raise FetchingError(
                'Cannot find versions of "{}" satisfying "{}" '
                'for the current target {}.'.format(name, spec, current_target)
            )

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
        if validate_managed_component_by_manifest(
            self.component_cache_path(component), component.component_hash
        ):
            copy_directory(self.component_cache_path(component), download_path)
            return download_path

        url = self._api_client.component(
            component_name=component.name, version=component.version
        ).download_url

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
            raise FetchingError(
                'Cannot download component {}@{}. {}'.format(
                    component.name, component.version, str(e)
                )
            )
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

        if self.__storage_url != IDF_COMPONENT_STORAGE_URL and self.__storage_url is not None:
            source['storage_url'] = self._storage_url

        if self.pre_release is not None:
            source['pre_release'] = self.pre_release

        return source
