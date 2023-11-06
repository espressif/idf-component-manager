# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from functools import wraps

from schema import Schema

import idf_component_tools as tools
from idf_component_tools.manifest import ComponentWithVersions, HashedComponentVersion
from idf_component_tools.messages import warn
from idf_component_tools.registry.api_client_errors import (
    ComponentNotFound,
    StorageFileNotFound,
    VersionNotFound,
)
from idf_component_tools.registry.api_schemas import COMPONENT_SCHEMA
from idf_component_tools.registry.base_client import BaseClient, create_session
from idf_component_tools.registry.component_details import ComponentDetailsWithStorageURL
from idf_component_tools.registry.request_processor import base_request, join_url
from idf_component_tools.semver import SimpleSpec, Version

try:
    from typing import Any, Callable, Optional
except ImportError:
    pass


def filter_versions(
    versions, version_filter, component_name
):  # type: (list[dict], str | None, str) -> list[dict]
    if version_filter and version_filter != '*':
        requested_version = SimpleSpec(str(version_filter))
        filtered_versions = [v for v in versions if requested_version.match(Version(v['version']))]

        if not filtered_versions or not any([bool(v.get('yanked_at')) for v in filtered_versions]):
            return filtered_versions

        clause = requested_version.clause.simplify()
        # Some clauses don't have an operator attribute, need to check
        if (
            hasattr(clause, 'operator')
            and clause.operator == '=='
            and filtered_versions[0]['yanked_at']
        ):
            warn(
                'The version "{}" of the "{}" component you have selected has '
                'been yanked from the repository due to the following reason: "{}". '
                'We recommend that you update to a different version. '
                'Please note that continuing to use a yanked version can '
                'result in unexpected behavior and issues with your project.'.format(
                    clause.target,
                    component_name.lower(),
                    filtered_versions[0]['yanked_message'],
                )
            )
        else:
            filtered_versions = [v for v in filtered_versions if not v.get('yanked_at')]
    else:
        filtered_versions = [v for v in versions if not v.get('yanked_at')]

    return filtered_versions


class ComponentWithVersionsAndStorageURL(ComponentWithVersions):
    def __init__(
        self, name, versions, storage_url
    ):  # type: (str, list[HashedComponentVersion], str | None) -> None
        super(ComponentWithVersionsAndStorageURL, self).__init__(name, versions)
        self.storage_url = storage_url

    @classmethod
    def from_component_with_versions(cls, cmp_with_versions, storage_url):
        return cls(cmp_with_versions.name, cmp_with_versions.versions, storage_url)


class StorageClient(BaseClient):
    def __init__(self, storage_url=None, sources=None):
        super(StorageClient, self).__init__(sources)
        self.storage_url = storage_url

    def _request(cache=False):  # type: (BaseClient | bool) -> Callable
        def decorator(f):  # type: (Callable[..., Any]) -> Callable
            @wraps(f)  # type: ignore
            def wrapper(self, *args, **kwargs):
                url = self.storage_url
                session = create_session(cache=cache)

                def request(
                    method,  # type: str
                    path,  # type: list[str]
                    data=None,  # type: dict | None
                    json=None,  # type: dict | None
                    headers=None,  # type: dict | None
                    schema=None,  # type: Schema | None
                ):
                    path[-1] += '.json'
                    return base_request(
                        url,
                        session,
                        method,
                        path,
                        data=data,
                        json=json,
                        headers=headers,
                        schema=schema,
                        use_storage=True,
                    )

                return f(self, request=request, *args, **kwargs)

            return wrapper

        return decorator

    @_request(cache=True)
    def versions(
        self, request, component_name, spec='*'
    ):  # type: (Callable, str, str) -> ComponentWithVersionsAndStorageURL
        """List of versions for given component with required spec"""
        try:
            cmp_with_versions = super(StorageClient, self).versions(
                request=request, component_name=component_name, spec=spec
            )
        except StorageFileNotFound:
            raise ComponentNotFound('Component "{}" not found'.format(component_name))

        return ComponentWithVersionsAndStorageURL.from_component_with_versions(
            cmp_with_versions, self.storage_url
        )

    @_request(cache=True)
    def component(
        self, request, component_name, version=None
    ):  # type: (Callable, str, str | None) -> ComponentDetailsWithStorageURL
        """
        Manifest for given version of component, if version is None highest version is returned
        """

        component_name = component_name.lower()
        try:
            response = request(
                'get', ['components', component_name.lower()], schema=COMPONENT_SCHEMA
            )
        except StorageFileNotFound:
            raise ComponentNotFound('Component "{}" not found'.format(component_name))

        versions = response['versions']
        filtered_versions = filter_versions(versions, version, component_name)

        if not filtered_versions:
            raise VersionNotFound(
                'Version of the component "{}" satisfying the spec "{}" was not found.'.format(
                    component_name, str(version)
                )
            )

        best_version = max(filtered_versions, key=lambda v: Version(v['version']))
        download_url = join_url(self.storage_url, best_version['url'])

        documents = best_version['docs']
        for document, url in documents.items():
            documents[document] = join_url(self.storage_url, url)

        license_info = best_version['license']
        license_name = None
        license_url = None
        if license_info:
            license_name = license_info['name']
            license_url = join_url(self.storage_url, license_info['url'])

        examples = best_version['examples']
        for example in examples:
            example.update({'url': join_url(self.storage_url, example['url'])})

        return ComponentDetailsWithStorageURL(
            name=('%s/%s' % (response['namespace'], response['name'])),
            version=tools.manifest.ComponentVersion(best_version['version']),
            dependencies=self._version_dependencies(best_version),
            maintainers=None,
            download_url=download_url,
            documents=documents,
            license_name=license_name,
            license_url=license_url,
            examples=examples,
            storage_url=self.storage_url,
        )
