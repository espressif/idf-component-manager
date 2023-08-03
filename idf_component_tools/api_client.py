# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Classes to work with Espressif Component Web Service"""
import os
import platform
import re
from collections import namedtuple
from functools import wraps
from io import open

import requests
from cachecontrol import CacheControlAdapter
from cachecontrol.caches import FileCache
from cachecontrol.heuristics import ExpiresAfter
from requests.adapters import HTTPAdapter
from requests_file import FileAdapter
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from schema import Schema, SchemaError
from tqdm import tqdm

# Import whole module to avoid circular dependencies
import idf_component_tools as tools
from idf_component_tools.__version__ import __version__
from idf_component_tools.environment import detect_ci, getenv_int
from idf_component_tools.errors import warn
from idf_component_tools.file_cache import FileCache as ComponentFileCache
from idf_component_tools.semver import SimpleSpec, Version

from .api_client_errors import (
    KNOWN_API_ERRORS,
    APIClientError,
    ComponentNotFound,
    NetworkConnectionError,
    NoRegistrySet,
    StorageFileNotFound,
    VersionNotFound,
)
from .api_schemas import (
    API_INFORMATION_SCHEMA,
    API_TOKEN_SCHEMA,
    COMPONENT_SCHEMA,
    ERROR_SCHEMA,
    TASK_STATUS_SCHEMA,
    VERSION_UPLOAD_SCHEMA,
)
from .manifest import BUILD_METADATA_KEYS, Manifest

try:
    from typing import TYPE_CHECKING, Any, Callable

    if TYPE_CHECKING:
        from idf_component_tools.sources import BaseSource
except ImportError:
    pass

TaskStatus = namedtuple('TaskStatus', ['message', 'status', 'progress', 'warnings'])

DEFAULT_TIMEOUT = (6.05, 30.1)  # Connect timeout  # Read timeout

DEFAULT_API_CACHE_EXPIRATION_MINUTES = 0
MAX_RETRIES = 3


def env_cache_time():
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


def filter_versions(
    versions, version_filter, component_name
):  # type: (list[dict], str, str) -> list[dict]
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


class ComponentDetails(Manifest):
    def __init__(
        self,
        download_url=None,  # type: str | None # Direct url for tarball download
        documents=None,  # type: list[dict[str, str]] | None # List of documents of the component
        license=None,  # type: dict[str, str] | None # Information about license
        examples=None,  # type: list[dict[str, str]] | None # List of examples of the component
        *args,
        **kwargs
    ):
        super(ComponentDetails, self).__init__(*args, **kwargs)
        self.download_url = download_url
        self.documents = documents
        self.license = license  # type: ignore
        self.examples = examples


def handle_4xx_error(error):  # type: (requests.Response) -> str
    try:
        json = ERROR_SCHEMA.validate(error.json())
        name = json['error']
        messages = json['messages']
    except SchemaError as e:
        raise APIClientError(
            'API Endpoint "{}: returned unexpected error description:\n{}'.format(error.url, str(e))
        )
    except ValueError:
        raise APIClientError('Server returned an error in unexpected format')

    exception = KNOWN_API_ERRORS.get(name, APIClientError)
    if isinstance(messages, list):
        raise exception('\n'.join(messages))
    else:
        raise exception(
            'Error during request:\n{}\nStatus code: {} Error code: {}'.format(
                str(messages), error.status_code, name
            )
        )


def join_url(*args):  # type: (*str) -> str
    """
    Joins given arguments into an url and add trailing slash
    """
    parts = [part[:-1] if part and part[-1] == '/' else part for part in args]
    return '/'.join(parts)


def auth_required(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if not self.auth_token:
            raise APIClientError('API token is required')
        return f(self, *args, **kwargs)

    return wrapper


class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token):  # type: (str | None) -> None
        self.token = token

    def __call__(self, request):
        if self.token:
            request.headers['Authorization'] = 'Bearer %s' % self.token
        return request


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


def _component_request(request, component_name):
    """Get component information from storage. Used by `versions` and `component`."""
    try:
        return request('get', ['components', component_name.lower()], schema=COMPONENT_SCHEMA)
    except StorageFileNotFound:
        raise ComponentNotFound('Component "{}" not found'.format(component_name))


class APIClient(object):
    def __init__(self, base_url=None, storage_url=None, source=None, auth_token=None):
        # type: (str | None, str | None, BaseSource | None, str | None) -> None
        self.base_url = base_url
        self._storage_url = storage_url
        self._frontend_url = None
        self.source = source
        self.auth_token = auth_token

    def _version_dependencies(self, version):
        dependencies = []
        for dependency in version.get('dependencies', []):
            # Support only idf and service sources
            if dependency['source'] == 'idf':
                source = tools.sources.IDFSource({})
            else:
                source = self.source or tools.sources.WebServiceSource({})

            dependencies.append(
                tools.manifest.ComponentRequirement(
                    name='{}/{}'.format(dependency['namespace'], dependency['name']),
                    version_spec=dependency['spec'],
                    public=dependency['is_public'],
                    source=source,
                )
            )

        return dependencies

    def _base_request(
        self,
        url,  # type: str
        session,  # type: requests.Session
        method,  # type: str
        path,  # type: list[str]
        data=None,  # type: dict | None
        json=None,  # type: dict | None
        headers=None,  # type: dict | None
        schema=None,  # type: Schema | None
        use_storage=False,  # type: bool
    ):
        # type: (...) -> dict
        endpoint = join_url(url, *path)

        timeout = DEFAULT_TIMEOUT  # type: float | tuple[float, float]
        try:
            timeout = float(os.environ['IDF_COMPONENT_SERVICE_TIMEOUT'])
        except ValueError:
            raise APIClientError(
                'Cannot parse IDF_COMPONENT_SERVICE_TIMEOUT. It should be a number in seconds.'
            )
        except KeyError:
            pass

        try:
            response = session.request(
                method,
                endpoint,
                data=data,
                json=json,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
            )

            if response.status_code == 204:  # NO CONTENT
                return {}
            elif 400 <= response.status_code < 500:
                if use_storage:
                    if response.status_code == 404:
                        raise StorageFileNotFound()
                    raise APIClientError(
                        'Error during request.\nStatus code: {}'.format(response.status_code)
                    )

                handle_4xx_error(response)

            elif 500 <= response.status_code < 600:
                raise APIClientError(
                    'Internal server error happended while processing '
                    'requrest to:\n{}\nStatus code: {}'.format(endpoint, response.status_code)
                )

            response_json = response.json()
        except requests.exceptions.ConnectionError as e:
            raise NetworkConnectionError(str(e))
        except requests.exceptions.RequestException:
            raise APIClientError('HTTP request error')

        try:
            if schema is not None:
                schema.validate(response_json)
        except SchemaError as e:
            raise APIClientError(
                'API Endpoint "{}: returned unexpected JSON:\n{}'.format(endpoint, str(e))
            )

        except (ValueError, KeyError, IndexError):
            raise APIClientError('Unexpected component server response')

        return response_json

    @property
    def storage_url(self):
        if not self._storage_url:
            self._storage_url = self.api_information()['components_base_url']
        return self._storage_url

    @property
    def frontend_url(self):
        if not self._frontend_url:
            self._frontend_url = re.sub(r'/api/?$', '', self.base_url)

        return self._frontend_url

    def _request(cache=False, use_storage=False):  # type: (APIClient | bool, bool) -> Callable
        def decorator(f):  # type: (Callable[..., Any]) -> Callable
            @wraps(f)  # type: ignore
            def wrapper(self, *args, **kwargs):
                url = self.base_url
                if use_storage:
                    url = self.storage_url

                if url is None:
                    raise NoRegistrySet(
                        'The current operation requires access to the IDF component registry. '
                        'However, the registry URL is not set. You can set the '
                        'IDF_COMPONENT_REGISTRY_URL environment variable or "registry_url" field '
                        'for your current profile in "idf_component_manager.yml" file. '
                        'To use the default IDF component registry '
                        'unset IDF_COMPONENT_STORAGE_URL environment variable or remove '
                        '"storage_url" field from the "idf_component_manager.yml" file'
                    )

                session = create_session(cache=cache, token=self.auth_token)

                def request(method, path, data=None, json=None, headers=None, schema=None):
                    if use_storage:
                        path[-1] += '.json'
                    return self._base_request(
                        url,
                        session,
                        method,
                        path,
                        data=data,
                        json=json,
                        headers=headers,
                        schema=schema,
                        use_storage=use_storage,
                    )

                return f(self, request=request, *args, **kwargs)

            return wrapper

        return decorator

    @_request(cache=True)
    def api_information(self, request):
        return request('get', [], schema=API_INFORMATION_SCHEMA)

    @auth_required
    @_request(cache=False)
    def token_information(self, request):
        return request('get', ['tokens', 'current'], schema=API_TOKEN_SCHEMA)

    @_request(cache=True, use_storage=True)
    def versions(self, request, component_name, spec='*'):
        """List of versions for given component with required spec"""

        component_name = component_name.lower()
        semantic_spec = SimpleSpec(spec or '*')
        body = _component_request(request, component_name)

        versions = []
        for version in body['versions']:
            if not semantic_spec.match(Version(version['version'])):
                continue

            all_build_keys_known = True
            if version.get('build_metadata_keys', None) is not None:
                for build_key in version.get('build_metadata_keys'):
                    if build_key not in BUILD_METADATA_KEYS:
                        all_build_keys_known = False
                        break

            if all_build_keys_known:
                versions.append((version, all_build_keys_known))

        return tools.manifest.ComponentWithVersions(
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

    @_request(cache=True, use_storage=True)
    def component(self, request, component_name, version=None):
        """
        Manifest for given version of component, if version is None highest version is returned
        """

        component_name = component_name.lower()
        response = _component_request(request, component_name)
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
        if license_info:
            license_info['url'] = join_url(self.storage_url, license_info['url'])

        examples = best_version['examples']
        for example in examples:
            example.update({'url': join_url(self.storage_url, example['url'])})

        return ComponentDetails(
            name=('%s/%s' % (response['namespace'], response['name'])),
            version=tools.manifest.ComponentVersion(best_version['version']),
            dependencies=self._version_dependencies(best_version),
            maintainers=None,
            download_url=download_url,
            documents=documents,
            license=license_info,
            examples=examples,
        )

    def _upload_version_to_endpoint(self, request, file_path, endpoint):
        with open(file_path, 'rb') as file:
            filename = os.path.basename(file_path)

            encoder = MultipartEncoder({'file': (filename, file, 'application/octet-stream')})
            headers = {'Content-Type': encoder.content_type}

            progress_bar = tqdm(total=encoder.len, unit_scale=True, unit='B', disable=None)

            def callback(
                monitor, memo={'progress': 0}
            ):  # type: (MultipartEncoderMonitor, dict) -> None
                progress_bar.update(monitor.bytes_read - memo['progress'])
                memo['progress'] = monitor.bytes_read

            data = MultipartEncoderMonitor(encoder, callback)

            try:
                return request(
                    'post',
                    endpoint,
                    data=data,
                    headers=headers,
                    schema=VERSION_UPLOAD_SCHEMA,
                )['job_id']
            finally:
                progress_bar.close()

    @auth_required
    @_request(cache=False)
    def upload_version(self, request, component_name, file_path):
        return self._upload_version_to_endpoint(
            request, file_path, ['components', component_name.lower(), 'versions']
        )

    @_request(cache=False)
    def validate_version(self, request, file_path):
        return self._upload_version_to_endpoint(request, file_path, ['components', 'validate'])

    @auth_required
    @_request(cache=False)
    def delete_version(self, request, component_name, component_version):
        request('delete', ['components', component_name.lower(), component_version])

    @auth_required
    @_request(cache=False)
    def yank_version(self, request, component_name, component_version, yank_message):
        request(
            'post',
            ['components', component_name.lower(), component_version, 'yank'],
            json={'message': yank_message},
        )

    @_request(cache=False)
    def task_status(self, request, job_id):  # type: (Callable, str) -> TaskStatus
        body = request('get', ['tasks', job_id], schema=TASK_STATUS_SCHEMA)
        return TaskStatus(
            body['message'], body['status'], body['progress'], body.get('warnings', [])
        )
