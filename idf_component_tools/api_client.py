# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Classes to work with Espressif Component Web Service"""
import os
import platform
from collections import namedtuple
from functools import wraps
from io import open

import requests
from cachecontrol import CacheControlAdapter
from cachecontrol.caches import FileCache
from cachecontrol.heuristics import ExpiresAfter
from requests.adapters import HTTPAdapter
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from schema import Schema, SchemaError
from tqdm import tqdm

# Import whole module to avoid circular dependencies
import idf_component_tools as tools
from idf_component_manager.utils import warn
from idf_component_tools import file_cache
from idf_component_tools.__version__ import __version__
from idf_component_tools.semver import SimpleSpec, Version

from .api_client_errors import KNOWN_API_ERRORS, APIClientError, ComponentNotFound
from .api_schemas import COMPONENT_SCHEMA, ERROR_SCHEMA, TASK_STATUS_SCHEMA, VERSION_UPLOAD_SCHEMA
from .manifest import Manifest

try:
    from typing import TYPE_CHECKING, Any, Callable, Tuple

    if TYPE_CHECKING:
        from idf_component_tools.sources import BaseSource
except ImportError:
    pass

TaskStatus = namedtuple('TaskStatus', ['message', 'status', 'progress'])

DEFAULT_TIMEOUT = (
    6.05,  # Connect timeout
    30.1,  # Read timeout
)

DEFAULT_API_CACHE_EXPIRATION = 180
MAX_RETRIES = 3


class ComponentDetails(Manifest):
    def __init__(
            self,
            download_url=None,  # type: str | None # Direct url for tarball download
            documents=None,  # type: list[dict[str, str]] | None # List of documents of the component
            license=None,  # type: dict[str, str] | None # Information about license
            examples=None,  # type: list[dict[str, str]] | None # List of examples of the component
            *args,
            **kwargs):
        super(ComponentDetails, self).__init__(*args, **kwargs)
        self.download_url = download_url
        self.documents = documents
        self.license = license
        self.examples = examples


def handle_4xx_error(error):  # type: (requests.Response) -> str
    try:
        json = ERROR_SCHEMA.validate(error.json())
        name = json['error']
        messages = json['messages']
    except SchemaError as e:
        raise APIClientError('API Endpoint "{}: returned unexpected error description:\n{}'.format(error.url, str(e)))
    except ValueError:
        raise APIClientError('Server returned an error in unexpected format')

    exception = KNOWN_API_ERRORS.get(name, APIClientError)
    if isinstance(messages, list):
        raise exception('\n'.join(messages))
    else:
        raise exception(
            'Error during request:\n{}\nStatus code: {} Error code: {}'.format(str(messages), error.status_code, name))


def join_url(*args):  # type: (*str) -> str
    """
    Joins given arguments into an url and add trailing slash
    """
    parts = [part[:-1] if part and part[-1] == '/' else part for part in args]
    parts.append('')
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
    return 'idf-component-manager/{version} ({os}/{release} {arch}; python/{py_version})'.format(
        version=__version__,
        os=platform.system(),
        release=platform.release(),
        arch=platform.machine(),
        py_version=platform.python_version(),
    )


class APIClient(object):
    def __init__(self, base_url, source=None, auth_token=None):
        # type: (str, BaseSource | None, str | None) -> None
        self.base_url = base_url
        self.source = source
        self.auth_token = auth_token
        try:
            self.cache_time = int(
                os.environ.get('IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES', DEFAULT_API_CACHE_EXPIRATION))
        except ValueError:
            warn(
                'IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES is set to a non-numeric value. '
                'Please set the variable to the number of minutes. '
                'Using the default value of {} minutes.'.format(DEFAULT_API_CACHE_EXPIRATION))
            self.cache_time = DEFAULT_API_CACHE_EXPIRATION

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
                ))

        return dependencies

    def _base_request(self, session, method, path, data=None, headers=None, schema=None):
        # type: (requests.Session, str, list[str], dict | None, dict | None, Schema | None) -> dict
        endpoint = join_url(self.base_url, *path)

        timeout = DEFAULT_TIMEOUT  # type: float | Tuple[float, float]
        try:
            timeout = float(os.environ['IDF_COMPONENT_SERVICE_TIMEOUT'])
        except ValueError:
            raise APIClientError('Cannot parse IDF_COMPONENT_SERVICE_TIMEOUT. It should be a number in seconds.')
        except KeyError:
            pass

        try:
            response = session.request(
                method,
                endpoint,
                data=data,
                headers=headers,
                timeout=timeout,
            )

            if response.status_code == 204:  # NO CONTENT
                return {}
            elif 400 <= response.status_code < 500:
                handle_4xx_error(response)

            elif 500 <= response.status_code < 600:
                raise APIClientError(
                    'Internal server error happended while processing requrest to:\n{}\nStatus code: {}'.format(
                        endpoint, response.status_code))

            json = response.json()
        except requests.exceptions.RequestException:
            raise APIClientError('HTTP request error')

        try:
            if schema is not None:
                schema.validate(json)
        except SchemaError as e:
            raise APIClientError('API Endpoint "{}: returned unexpected JSON:\n{}'.format(endpoint, str(e)))

        except (ValueError, KeyError, IndexError):
            raise APIClientError('Unexpected component server response')

        return json

    def _create_session(
            self,
            cache=False,  # type: bool
            cache_path=file_cache.FileCache.path()  # type: str
    ):  # type: (...) -> requests.Session
        if cache:
            api_adapter = CacheControlAdapter(
                max_retries=MAX_RETRIES,
                heuristic=ExpiresAfter(minutes=self.cache_time),
                cache=FileCache(os.path.join(cache_path, '.api_client')))
        else:
            api_adapter = HTTPAdapter(max_retries=MAX_RETRIES)

        session = requests.Session()
        session.headers['User-Agent'] = user_agent()
        session.auth = TokenAuth(self.auth_token)
        session.mount(self.base_url, api_adapter)

        return session

    def _request(cache=False):  # type: ignore
        def decorator(f):  # type: (APIClient | Callable[..., Any]) -> Callable
            @wraps(f)  # type: ignore
            def wrapper(self, *args, **kwargs):
                cache_status = cache and bool(self.cache_time)
                session = self._create_session(cache=cache_status)

                def request(method, path, data=None, headers=None, schema=None):
                    return self._base_request(session, method, path, data=data, headers=headers, schema=schema)

                return f(self, request=request, *args, **kwargs)

            return wrapper

        return decorator

    @_request(cache=True)  # type: ignore
    def versions(self, request, component_name, spec='*', target=None):
        """List of versions for given component with required spec"""
        semantic_spec = SimpleSpec(spec or '*')
        component_name = component_name.lower()
        try:
            body = request(
                'get',
                ['components', component_name],
                schema=COMPONENT_SCHEMA,
            )
        except ComponentNotFound:
            versions = []
        else:
            versions = []
            for version in body['versions']:
                if semantic_spec.match(Version(version['version'])):
                    if target and version['targets'] and target not in version['targets']:
                        continue
                    versions.append(version)

        return tools.manifest.ComponentWithVersions(
            name=component_name,
            versions=[
                tools.manifest.HashedComponentVersion(
                    version_string=version['version'],
                    component_hash=version['component_hash'],
                    dependencies=self._version_dependencies(version),
                    targets=version['targets'],
                ) for version in versions
            ],
        )

    @_request(cache=True)  # type: ignore
    def component(self, request, component_name, version=None):
        """Manifest for given version of component, if version is None most recent version returned"""
        response = request(
            'get',
            ['components', component_name.lower()],
            schema=COMPONENT_SCHEMA,
        )
        versions = response['versions']

        if version:
            requested_version = tools.manifest.ComponentVersion(str(version))
            best_version = [v for v in versions
                            if tools.manifest.ComponentVersion(v['version']) == requested_version][0]
        else:
            best_version = max(versions, key=lambda v: Version(v['version']))

        return ComponentDetails(
            name=('%s/%s' % (response['namespace'], response['name'])),
            version=tools.manifest.ComponentVersion(best_version['version']),
            dependencies=self._version_dependencies(best_version),
            maintainers=None,
            download_url=best_version['url'],
            documents=best_version['docs'],
            license=best_version['license'],
            examples=best_version['examples'])

    @auth_required
    @_request(cache=False)  # type: ignore
    def upload_version(self, request, component_name, file_path):
        with open(file_path, 'rb') as file:
            filename = os.path.basename(file_path)

            encoder = MultipartEncoder({'file': (filename, file, 'application/octet-stream')})
            headers = {'Content-Type': encoder.content_type}

            progress_bar = tqdm(total=encoder.len, unit_scale=True, unit='B', disable=None)

            def callback(monitor, memo={'progress': 0}):  # type: (MultipartEncoderMonitor, dict) -> None
                progress_bar.update(monitor.bytes_read - memo['progress'])
                memo['progress'] = monitor.bytes_read

            data = MultipartEncoderMonitor(encoder, callback)

            try:
                return request(
                    'post',
                    ['components', component_name.lower(), 'versions'],
                    data=data,
                    headers=headers,
                    schema=VERSION_UPLOAD_SCHEMA,
                )['job_id']
            finally:
                progress_bar.close()

    @auth_required
    @_request(cache=False)  # type: ignore
    def delete_version(self, request, component_name, component_version):
        request('delete', ['components', component_name.lower(), component_version])

    @_request(cache=False)  # type: ignore
    def task_status(self, request, job_id):  # type: (Callable, str) -> TaskStatus
        body = request('get', ['tasks', job_id], schema=TASK_STATUS_SCHEMA)
        return TaskStatus(body['message'], body['status'], body['progress'])
