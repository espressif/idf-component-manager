# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import platform

import requests
from cachecontrol import CacheControlAdapter
from cachecontrol.caches import FileCache
from cachecontrol.heuristics import ExpiresAfter
from requests.adapters import HTTPAdapter
from requests_file import FileAdapter

import idf_component_tools as tools
from idf_component_tools.__version__ import __version__
from idf_component_tools.environment import detect_ci, getenv_int
from idf_component_tools.file_cache import FileCache as ComponentFileCache
from idf_component_tools.messages import warn
from idf_component_tools.semver import SimpleSpec, Version

from ..manifest import BUILD_METADATA_KEYS, ComponentWithVersions
from .api_schemas import COMPONENT_SCHEMA
from .token_auth import TokenAuth

try:
    from typing import Callable
except ImportError:
    pass

DEFAULT_API_CACHE_EXPIRATION_MINUTES = 0
MAX_RETRIES = 3


def env_cache_time():  # type: () -> int
    try:
        return getenv_int(
            'IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES',
            DEFAULT_API_CACHE_EXPIRATION_MINUTES,
        )
    except ValueError:
        warn(
            'IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES is set to a non-numeric value. '
            'Please set the variable to the number of minutes. Disabling caching.'
        )
        return DEFAULT_API_CACHE_EXPIRATION_MINUTES


def create_session(
    cache=False,  # type: bool
    cache_path=None,  # type: str | None
    cache_time=None,  # type: int | None
    token=None,  # type: str | None
):  # type: (...) -> requests.Session
    if cache_path is None:
        cache_path = ComponentFileCache().path()

    cache_time = cache_time or env_cache_time()
    if cache and cache_time:
        api_adapter = CacheControlAdapter(
            max_retries=MAX_RETRIES,
            heuristic=ExpiresAfter(minutes=cache_time),
            cache=FileCache(os.path.join(cache_path, '.api_client')),
        )
    else:
        api_adapter = HTTPAdapter(max_retries=MAX_RETRIES)

    session = requests.Session()
    session.headers['User-Agent'] = user_agent()
    session.auth = TokenAuth(token)

    session.mount('http://', api_adapter)
    session.mount('https://', api_adapter)
    session.mount('file://', FileAdapter())

    return session


def user_agent():  # type: () -> str
    """
    Returns user agent string.
    """

    environment_info = [
        '{os}/{release} {arch}'.format(
            os=platform.system(), release=platform.release(), arch=platform.machine()
        ),
        'python/{version}'.format(version=platform.python_version()),
    ]

    ci_name = detect_ci()
    if ci_name:
        environment_info.append('ci/{}'.format(ci_name))

    user_agent = 'idf-component-manager/{version} ({env})'.format(
        version=__version__,
        env='; '.join(environment_info),
    )

    return user_agent


class BaseClient(object):
    def __init__(self, sources=None):
        self.sources = sources

    def _version_dependencies(self, version):
        dependencies = []
        for dependency in version.get('dependencies', []):
            # Support only idf and service sources
            if dependency['source'] == 'idf':
                sources = [tools.sources.IDFSource({})]
            else:
                sources = self.sources or [tools.sources.WebServiceSource({})]

            is_public = dependency.get('is_public', False)
            require = dependency.get('require', True)
            require_string = 'public' if is_public else ('private' if require else 'no')

            dependencies.append(
                tools.manifest.ComponentRequirement(
                    name='{}/{}'.format(dependency['namespace'], dependency['name']),
                    version_spec=dependency['spec'],
                    sources=sources,
                    public=is_public,
                    require=require_string,
                    optional_requirement=tools.manifest.OptionalRequirement.fromdict(dependency),
                )
            )

        return tools.manifest.filter_optional_dependencies(dependencies)

    def versions(
        self, request, component_name, spec='*'
    ):  # type: (Callable, str, str) -> ComponentWithVersions
        """List of versions for given component with required spec"""
        component_name = component_name.lower()
        semantic_spec = SimpleSpec(spec or '*')
        body = request('get', ['components', component_name.lower()], schema=COMPONENT_SCHEMA)

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
                tools.manifest.HashedComponentVersion(
                    version_string=version['version'],
                    component_hash=version['component_hash'],
                    dependencies=self._version_dependencies(version),
                    targets=version['targets'],
                    all_build_keys_known=all_build_keys_known,
                )
                for version, all_build_keys_known in versions
            ],
        )


def filter_versions(
    versions, spec, component_name
):  # type: (list[dict], str | None, str) -> list[dict]
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
