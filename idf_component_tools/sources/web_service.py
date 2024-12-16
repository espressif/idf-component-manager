# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Component source that downloads components from web service"""

import os
import re
import shutil
import tempfile
import typing as t
from http import HTTPStatus
from pathlib import Path

import requests
from pydantic import AliasChoices, Field, field_validator

from idf_component_tools import debug, hint
from idf_component_tools.archive_tools import (
    get_archive_extension,
    unpack_archive,
)
from idf_component_tools.config import get_registry_url
from idf_component_tools.constants import (
    DEFAULT_NAMESPACE,
    IDF_COMPONENT_REGISTRY_URL,
    UPDATE_SUGGESTION,
)
from idf_component_tools.debugger import DEBUG_INFO_COLLECTOR
from idf_component_tools.errors import FetchingError
from idf_component_tools.file_tools import copy_directory, get_file_extension
from idf_component_tools.hash_tools.calculate import hash_url
from idf_component_tools.hash_tools.checksums import ChecksumsManager, ChecksumsModel
from idf_component_tools.hash_tools.constants import CHECKSUMS_FILENAME
from idf_component_tools.hash_tools.errors import ChecksumsParseError, ValidatingHashError
from idf_component_tools.hash_tools.validate import (
    validate_hash_eq_hashdir,
)
from idf_component_tools.semver import SimpleSpec
from idf_component_tools.utils import Literal

from .base import BaseSource

if t.TYPE_CHECKING:
    from idf_component_tools.manifest import SolvedComponent


CANONICAL_IDF_COMPONENT_REGISTRY_API_URL = 'https://api.components.espressif.com/'


def download_file(
    url: str,
    download_dir: str,
    filename: t.Optional[str] = None,
    use_original_extension: bool = False,
    get_extension_cb: t.Optional[t.Callable[[str], t.Optional[str]]] = None,
) -> str:
    """Download file from URL to the specified directory.

    :param url: URL to download file from
    :param download_dir: download directory
    :param filename: name of the file, defaults to None
    :param use_original_extension: use original extension from URL, defaults to False
    :param get_extension_cb: callback to get file extension, defaults to None
    :raises FetchingError: If server returned bad HTTP status or something was wrong while fetching the file.
    :return: Path to downloaded file.
    """

    from idf_component_tools.registry.base_client import (
        create_session,
    )

    session = create_session()

    try:
        with session.get(url, stream=True, allow_redirects=True) as r:
            if r.status_code != HTTPStatus.OK:
                raise FetchingError(
                    f'Server returned HTTP code {r.status_code} while downloading {url}'
                )

            get_extension_fn = get_extension_cb or get_file_extension

            # Trying to get extension from url
            original_filename = url.split('/')[-1]
            original_extension = get_extension_fn(original_filename)

            # If didn't find anything useful, trying content disposition
            content_disposition = r.headers.get('content-disposition')
            if not original_extension and content_disposition:
                filenames = re.findall('filename=(.+)', content_disposition)
                try:
                    original_extension = get_extension_fn(filenames[0])
                except IndexError:
                    raise FetchingError('Server returned invalid download URL')

            original_extension = original_extension or ''
            new_filename = original_filename

            if filename:
                if get_file_extension(filename) or not use_original_extension:
                    new_filename = filename
                else:
                    new_filename = f'{filename}{original_extension}'

            tmp_file_path = os.path.join(download_dir, f'{new_filename}.tmp')

            with open(tmp_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            file_path = os.path.join(download_dir, new_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            shutil.move(tmp_file_path, file_path)

            return file_path

    except requests.exceptions.RequestException as e:
        raise FetchingError(str(e))


def download_archive(url: str, download_dir: str, save_original_filename: bool = False) -> str:
    """Download archive from URL to the specified directory.

    :param url: URL to download archive from
    :param download_dir: download directory
    :param save_original_filename: save original filename, defaults to False
    :raises FetchingError: If server returned bad HTTP status or something was wrong while fetching the file.
    :return: Path to downloaded archive.
    """

    return download_file(
        url,
        download_dir,
        filename=('component' if not save_original_filename else None),
        use_original_extension=True,
        get_extension_cb=get_archive_extension,
    )


class WebServiceSource(BaseSource):
    registry_url: str = Field(
        default_factory=get_registry_url,
        validation_alias=AliasChoices(
            'registry_url',
            'service_url',
        ),
    )  # type: ignore
    type: Literal['service'] = 'service'  # type: ignore
    pre_release: bool = None  # type: ignore

    def __repr__(self) -> str:
        return f'{self.type}({self.registry_url})'

    @field_validator('registry_url')
    @classmethod
    def validate_registry_url(cls, v):
        # Use registry url for lock file
        if not v or v == CANONICAL_IDF_COMPONENT_REGISTRY_API_URL:
            return IDF_COMPONENT_REGISTRY_URL

        # if url endswith /api, remove it
        if v.endswith('/api'):
            return v[:-4]

        return v

    @property
    def hash_key(self):
        if self._hash_key is None:
            self._hash_key = hash_url(self.registry_url)
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

        client = get_storage_client(self.registry_url)
        if client.registry_url != self.registry_url:
            client.registry_url = self.registry_url

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
            debugger = DEBUG_INFO_COLLECTOR.get()
            if pre_release_versions:
                debugger.add_msg(
                    'Component "{}" (requires in {}) '
                    'has some pre-release versions: "{}" '
                    'satisfies your requirements. '
                    'To allow pre-release versions add "pre_release: true" '
                    'to the dependency in the manifest.'.format(
                        name,
                        ', '.join(debugger.dep_introduced_by[name]),
                        '", "'.join(pre_release_versions),
                    )
                )

            if other_targets_versions:
                version_t_list = ''
                for v in other_targets_versions:
                    version_t_list += f'- {v.version}: {", ".join(v.targets)}\n'

                debugger.add_msg(
                    'Component "{}" (requires in {}) '
                    'has suitable versions for other targets:\n'
                    '{}'
                    'Is your current target {} set correctly?'.format(
                        name,
                        ', '.join(debugger.dep_introduced_by[name]),
                        version_t_list,
                        target or '',
                    )
                )

            if newer_component_manager_versions:
                debugger.add_msg(
                    'Component "{}" (requires in {}) '
                    'has versions "{}" '
                    'that support only newer version of idf-component-manager '
                    'that satisfy your requirements.\n'
                    '{}'.format(
                        name,
                        ', '.join(debugger.dep_introduced_by[name]),
                        '", "'.join(newer_component_manager_versions),
                        UPDATE_SUGGESTION,
                    )
                )

        return cmp_with_versions

    @property
    def downloadable(self) -> bool:
        return True

    def normalized_name(self, name):
        if '/' not in name:
            name = '/'.join([DEFAULT_NAMESPACE, name])

        return name

    def download(self, component: 'SolvedComponent', download_path: str) -> str:
        from idf_component_tools.registry.service_details import get_storage_client

        # Check for required components
        if not component.component_hash:
            raise FetchingError(
                'Component hash is required for components from the ESP Component Registry'
            )

        if not component.version:
            raise FetchingError(f'Version should be provided for {component.name}')

        # Check if component is in the cache
        component_cache_path = self.component_cache_path(component)

        if os.path.exists(component_cache_path) and os.path.isdir(component_cache_path):
            try:
                validate_hash_eq_hashdir(component_cache_path, component.component_hash)
                copy_directory(component_cache_path, download_path)
                return download_path
            except ValidatingHashError:
                pass

        tempdir = tempfile.mkdtemp()

        url = get_storage_client(self.registry_url).component(component.name, component.version)[
            'download_url'
        ]  # PACMAN-906

        storage_client_component = get_storage_client(self.registry_url).component(
            component.name, component.version
        )
        url = storage_client_component['download_url']
        checksums_url = storage_client_component['checksums_url']

        try:
            debug(
                'Downloading component %s@%s from %s',
                component.name,
                component.version,
                url,
            )

            # Download archive, unpack to the cache directory and copy to the download directory
            archive_path = download_archive(url, tempdir)
            unpack_archive(archive_path, component_cache_path)
            copy_directory(component_cache_path, download_path)

            debug(
                'Downloading checksums for component %s@%s from %s',
                component.name,
                component.version,
                checksums_url,
            )

            # Download file hashes and copy to cache and download directories
            checksums_path = download_file(checksums_url, tempdir, filename=CHECKSUMS_FILENAME)
            shutil.copy2(checksums_path, component_cache_path)
            shutil.copy2(checksums_path, download_path)
        except (KeyError, FetchingError) as e:
            hint(
                'The download failure may be caused by corrupted local storage. Please check manually.'
            )
            raise FetchingError(
                'Cannot download component {}@{}. {}'.format(
                    component.name, component.version, str(e)
                )
            )
        finally:
            shutil.rmtree(tempdir)

        return download_path

    def version_checksums(self, component: 'SolvedComponent') -> t.Optional[ChecksumsModel]:
        from idf_component_tools.registry.service_details import get_storage_client

        storage_client_component = get_storage_client(self.registry_url).component(
            component.name, component.version
        )
        checksums_url = storage_client_component['checksums_url']

        tempdir = tempfile.mkdtemp()
        try:
            download_file(checksums_url, tempdir, filename=CHECKSUMS_FILENAME)
            checksums_manager = ChecksumsManager(Path(tempdir))
            checksums = checksums_manager.load()
        except FetchingError as e:
            raise FetchingError(
                'Cannot download checksums for component {}@{}. {}'.format(
                    component.name, component.version, str(e)
                )
            )
        except ChecksumsParseError as e:
            raise ChecksumsParseError(
                'Cannot parse checksums for component {}@{}. {}'.format(
                    component.name, component.version, str(e)
                )
            )
        finally:
            shutil.rmtree(tempdir)

        return checksums
