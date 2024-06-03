# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import platform
import typing as t

import requests
from requests.adapters import HTTPAdapter
from requests.auth import AuthBase
from requests_file import FileAdapter

from idf_component_tools.__version__ import __version__
from idf_component_tools.constants import DEFAULT_NAMESPACE, IDF_COMPONENT_REGISTRY_URL
from idf_component_tools.environment import detect_ci
from idf_component_tools.manifest import BUILD_METADATA_KEYS, ComponentRequirement
from idf_component_tools.messages import warn
from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.utils import (
    ComponentWithVersions,
    HashedComponentVersion,
)

from .api_models import ComponentResponse

MAX_RETRIES = 3


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

    def version_dependencies(self, version: t.Dict[str, t.Any]) -> t.List[ComponentRequirement]:
        deps: t.List[ComponentRequirement] = []
        for dependency in version.get('dependencies', []):
            # make it compatible with the old format
            dependency['name'] = f'{dependency.pop("namespace")}/{dependency.pop("name")}'

            is_public = dependency.pop('is_public', False)
            require = dependency.pop('require', True)
            dependency['require'] = 'public' if is_public else ('private' if require else 'no')

            dependency['version'] = dependency.pop('spec')

            source_str = dependency.pop('source')
            if source_str == 'idf':
                dependency['name'] = 'idf'
            elif source_str == 'service':
                dependency['registry_url'] = IDF_COMPONENT_REGISTRY_URL
            else:
                raise ValueError('Unknown source type, Internal error')

            dep = ComponentRequirement.fromdict(dependency)
            deps.append(dep)
        return [dep for dep in deps if dep.meet_optional_dependencies]

    def versions(
        self,
        request: t.Callable,
        component_name: str,
        spec: str = '*',
        **kwargs,
    ) -> ComponentWithVersions:
        """List of versions for given component with required spec"""
        component_name = component_name.lower()
        semantic_spec = SimpleSpec(spec or '*')
        body = request('get', ['components', component_name.lower()], schema=ComponentResponse)

        versions = []
        filtered_versions = filter_versions(body['versions'], spec, component_name)

        for version in filtered_versions:
            if not semantic_spec.match(Version(version['version'])):
                continue

            all_build_keys_known = True
            if version.get('build_metadata_keys', None) is not None:
                for build_key in version['build_metadata_keys']:
                    if build_key not in BUILD_METADATA_KEYS:
                        all_build_keys_known = False
                        break

            if all_build_keys_known:
                versions.append((version, all_build_keys_known))

        return ComponentWithVersions(
            name=component_name,
            versions=[
                HashedComponentVersion(
                    version_string=version['version'],
                    component_hash=version['component_hash'],
                    dependencies=self.version_dependencies(version),
                    targets=version['targets'],
                    all_build_keys_known=all_build_keys_known,
                    **kwargs,
                )
                for version, all_build_keys_known in versions
            ],
        )


def filter_versions(
    versions: t.List[t.Dict], spec: t.Optional[str], component_name: str
) -> t.List[t.Dict]:
    if spec and spec != '*':
        requested_version = SimpleSpec(str(spec))
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


class TokenAuth(AuthBase):
    def __init__(self, token: t.Optional[str]) -> None:
        self.token = token

    def __call__(self, request):
        if self.token:
            request.headers['Authorization'] = f'Bearer {self.token}'
        return request
