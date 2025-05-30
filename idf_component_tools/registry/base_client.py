# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import platform
import typing as t
from functools import lru_cache

import requests
from requests.adapters import HTTPAdapter
from requests.auth import AuthBase
from requests_file import FileAdapter

from idf_component_tools.__version__ import __version__
from idf_component_tools.constants import DEFAULT_NAMESPACE
from idf_component_tools.environment import detect_ci
from idf_component_tools.manifest import BUILD_METADATA_KEYS, ComponentRequirement
from idf_component_tools.messages import warn
from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.utils import (
    ComponentWithVersions,
    HashedComponentVersion,
)

from .api_models import ComponentResponse, VersionResponse

MAX_RETRIES = 3


@lru_cache(maxsize=None)
def create_session(
    token: t.Optional[str] = None,
) -> requests.Session:
    api_adapter = HTTPAdapter(max_retries=MAX_RETRIES)

    session = requests.Session()
    session.headers['User-Agent'] = user_agent()
    session.auth = TokenAuth(token)

    session.mount('http://', api_adapter)
    session.mount('https://', api_adapter)
    session.mount('file://', FileAdapter())

    return session


def user_agent() -> str:
    """
    Returns user agent string.
    """

    environment_info = [
        f'{platform.system()}/{platform.release()} {platform.machine()}',
        f'python/{platform.python_version()}',
    ]

    ci_name = detect_ci()
    if ci_name:
        environment_info.append(f'ci/{ci_name}')

    user_agent = 'idf-component-manager/{version} ({env})'.format(
        version=__version__,
        env='; '.join(environment_info),
    )

    return user_agent


class BaseClient:
    def __init__(self, default_namespace: t.Optional[str]) -> None:
        self.default_namespace = default_namespace or DEFAULT_NAMESPACE

    def versions(self, component_name: str, spec: str = '*') -> ComponentWithVersions:
        """List of versions for given component with required spec"""
        spec = spec or '*'

        component_response = self.get_component_response(  # type: ignore
            # request is passed in subclasses
            component_name=component_name,
        )

        versions: t.List[t.Tuple[VersionResponse, bool]] = []
        filtered_versions = filter_versions(component_response.versions, spec, component_name)

        for version in filtered_versions:
            all_build_keys_known = True
            if version.build_metadata_keys is not None:
                for build_key in version.build_metadata_keys:
                    if build_key not in BUILD_METADATA_KEYS:
                        all_build_keys_known = False
                        break

            versions.append((version, all_build_keys_known))

        return ComponentWithVersions(
            name=component_name,
            versions=[
                HashedComponentVersion(
                    version_string=version.version,
                    component_hash=version.component_hash,
                    dependencies=[
                        ComponentRequirement.from_dependency_response(dep)
                        for dep in version.dependencies
                    ],
                    targets=version.targets or [],
                    all_build_keys_known=all_build_keys_known,
                )
                for version, all_build_keys_known in versions
            ],
        )

    def get_component_response(
        self, request: t.Callable, component_name: str, spec: str = '*'
    ) -> ComponentResponse:
        """
        Get component response for given component name and spec.
        Versions are sorted by semver, descending.
        """
        component_name = component_name.lower()
        spec = spec or '*'

        component_response = ComponentResponse(**request('get', ['components', component_name]))

        # here we don't use filter_versions because we don't need to
        # filter by target
        # filter yanked versions
        if spec != '*':
            versions = []
            required_spec = SimpleSpec(spec)
            for version in component_response.versions:
                if not required_spec.match(Version(version.version)):
                    continue
                versions.append(version)

            component_response.versions = versions

        component_response.versions = sorted(
            component_response.versions, key=lambda v: Version(v.version), reverse=True
        )

        return component_response


def filter_versions(
    versions: t.List[VersionResponse],
    spec: t.Optional[str],
    component_name: str,
) -> t.List[VersionResponse]:
    component_name = component_name.lower()
    filtered_versions = []
    yanked_versions = []

    # filter by spec
    required_spec = SimpleSpec(str(spec or '*'))
    versions = [version for version in versions if required_spec.match(Version(version.version))]

    # divide versions into yanked and not yanked
    for version in versions:
        if version.yanked_at:
            yanked_versions.append(version)
        else:
            filtered_versions.append(version)

    if filtered_versions:
        return filtered_versions

    # special case: use "==" and only selected yanked versions
    simplified_clause = required_spec.clause.simplify()
    if (
        hasattr(simplified_clause, 'operator')
        and simplified_clause.operator == '=='
        and len(yanked_versions) > 0
        and not filtered_versions
    ):
        warn_str = f'The following versions of the "{component_name}" component have been yanked:\n'
        for yanked_version in yanked_versions:
            warn_str += f'- {yanked_version.version} (reason: "{yanked_version.yanked_message}")\n'
        warn_str += (
            'We recommend that you update to a different version. '
            'Please note that continuing to use a yanked version can '
            'result in unexpected behavior and issues with your project.'
        )
        warn(warn_str)
        return yanked_versions

    return filtered_versions


class TokenAuth(AuthBase):
    def __init__(self, token: t.Optional[str]) -> None:
        self.token = token

    def __call__(self, request):
        if self.token:
            request.headers['Authorization'] = f'Bearer {self.token}'
        return request
