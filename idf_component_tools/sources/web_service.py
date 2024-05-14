# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Component source that downloads components from web service"""

import os
import re
import shutil
import tempfile
import typing as t

import requests
from pydantic import field_validator

from idf_component_tools.archive_tools import ArchiveError, get_format_from_path, unpack_archive
from idf_component_tools.constants import (
    DEFAULT_NAMESPACE,
    IDF_COMPONENT_REGISTRY_URL,
    UPDATE_SUGGESTION,
)
from idf_component_tools.errors import FetchingError
from idf_component_tools.file_tools import copy_directory
from idf_component_tools.hash_tools.calculate import hash_url
from idf_component_tools.messages import hint
from idf_component_tools.semver import SimpleSpec

from .base import BaseSource

if t.TYPE_CHECKING:
    from idf_component_tools.manifest import SolvedComponent

from idf_component_tools.utils import Literal

CANONICAL_IDF_COMPONENT_REGISTRY_API_URL = 'https://api.components.espressif.com/'


def download_archive(url: str, download_dir: str, save_original_filename: bool = False) -> str:
    from idf_component_tools.registry.base_client import create_session  # avoid circular import

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
                raise FetchingError(f'Server returned HTTP code {r.status_code}')

            # If didn't find anything useful, trying content disposition
            content_disposition = r.headers.get('content-disposition')
            if not extension and content_disposition:
                filenames = re.findall('filename=(.+)', content_disposition)
                try:
                    extension = get_format_from_path(filenames[0])[1]
                except IndexError:
                    raise FetchingError('Web Service returned invalid download url')

            filename = original_filename
            if not save_original_filename:
                filename = f'component.{extension}'

            tmp_file_path = os.path.join(download_dir, f'{filename}.tmp')

            with open(tmp_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            file_path = os.path.join(download_dir, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            shutil.move(tmp_file_path, file_path)

            return file_path
    except requests.exceptions.RequestException as e:
        raise FetchingError(str(e))


class WebServiceSource(BaseSource):
    service_url: str = None  # type: ignore
    type: Literal['service'] = 'service'  # type: ignore
    pre_release: bool = None  # type: ignore

    @field_validator('service_url')
    @classmethod
    def validate_service_url(cls, v):
        # Use canonical API url for lock file
        if not v or v == IDF_COMPONENT_REGISTRY_URL:
            return CANONICAL_IDF_COMPONENT_REGISTRY_API_URL

        return v

    def model_post_init(self, __context: t.Any) -> None:
        if not self.base_url:
            FetchingError('Cannot fetch a dependency with when registry is not defined')

    @property
    def base_url(self) -> str:
        # Use the default URL, even if the lock file was made with the canonical one
        return (
            IDF_COMPONENT_REGISTRY_URL
            if self.service_url == CANONICAL_IDF_COMPONENT_REGISTRY_API_URL
            else self.service_url
        ) or IDF_COMPONENT_REGISTRY_URL

    @property
    def hash_key(self):
        if self._hash_key is None:
            self._hash_key = hash_url(self.base_url)
        return self._hash_key

    def component_cache_path(self, component: 'SolvedComponent') -> str:
        component_dir_name = '_'.join([
            self.normalized_name(component.name).replace('/', '__'),
            str(component.version),
            str(component.component_hash)[:8],
        ])
        path = os.path.join(self.cache_path(), component_dir_name)
        return path

    def versions(self, name, spec='*', target=None):
        from idf_component_tools.registry.service_details import (
            get_storage_client,  # avoid circular import
        )

        client = get_storage_client(self.base_url)
        if self.base_url != client.registry_url:
            client.registry_url = self.base_url

        cmp_with_versions = client.versions(component_name=self.normalized_name(name), spec=spec)

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
            current_target = f'"{target}"' if target else ''

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

        return cmp_with_versions

    @property
    def component_hash_required(self) -> bool:
        return True

    @property
    def downloadable(self) -> bool:
        return True

    def normalized_name(self, name):
        if '/' not in name:
            name = '/'.join([DEFAULT_NAMESPACE, name])

        return name

    def download(self, component: 'SolvedComponent', download_path: str) -> str:
        from idf_component_tools.hash_tools.validate_managed_component import (
            validate_managed_component_by_manifest,  # avoid circular import
        )
        from idf_component_tools.registry.storage_client import (
            StorageClient,  # avoid circular import
        )

        # Check for required components
        if not component.component_hash:
            raise FetchingError('Component hash is required for components from web service')

        if not component.version:
            raise FetchingError(f'Version should be provided for {component.name}')

        if self.up_to_date(component, download_path):
            return download_path

        # Check if component is in the cache
        if validate_managed_component_by_manifest(
            self.component_cache_path(component), component.component_hash
        ):
            copy_directory(self.component_cache_path(component), download_path)
            return download_path

        tempdir = tempfile.mkdtemp()
        try:
            url = StorageClient(component.download_url).component(
                component.name, component.version
            )['download_url']

            file_path = download_archive(url, tempdir)
            unpack_archive(file_path, self.component_cache_path(component))
            copy_directory(self.component_cache_path(component), download_path)
        except (KeyError, FetchingError) as e:
            raise FetchingError(
                'Cannot download component {}@{}. {}'.format(
                    component.name, component.version, str(e)
                )
            )
        finally:
            shutil.rmtree(tempdir)

        return download_path
