"""Classes to work with Espressif Component Web Service"""
import os
from collections import namedtuple
from io import open

import requests
import semantic_version as semver
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from tqdm import tqdm

# Import whole module to avoid circular dependencies
import idf_component_tools as tools

TaskStatus = namedtuple('TaskStatus', ['message', 'status', 'progress'])


class APIClientError(Exception):
    pass


def join_url(*args):  # type: (*str) -> str
    """
    Joins given arguments into an url and add trailing slash
    """
    parts = [part[:-1] if part and part[-1] == '/' else part for part in args]
    parts.append('')
    return '/'.join(parts)


class APIClient(object):
    def __init__(self, base_url, source=None, auth_token=None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.auth_header = {'Authorization': 'Bearer %s' % auth_token}
        self.source = source

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

    def versions(self, component_name, spec='*'):
        """List of versions for given component with required spec"""
        component_name = component_name.lower()

        endpoint = join_url(self.base_url, 'components', component_name)

        try:
            response = requests.get(endpoint)
            response.raise_for_status()

            body = response.json()

            return tools.manifest.ComponentWithVersions(
                name=component_name,
                versions=[
                    tools.manifest.HashedComponentVersion(
                        version_string=version['version'],
                        component_hash=version['component_hash'],
                        dependencies=self._version_dependencies(version),
                    ) for version in body['versions']
                ],
            )

        except requests.exceptions.RequestException:
            raise APIClientError('HTTP request error')

        except KeyError:
            raise APIClientError('Unexpected component server response')

    def component(self, component_name, version=None):
        """Manifest for given version of component, if version is None most recent version returned"""

        endpoint = join_url(self.base_url, 'components', component_name.lower())

        try:
            raw_response = requests.get(endpoint)
            raw_response.raise_for_status()
            response = raw_response.json()
            versions = response['versions']

            if version:
                requested_version = tools.manifest.ComponentVersion(str(version))
                best_version = [
                    v for v in versions if tools.manifest.ComponentVersion(v['version']) == requested_version
                ][0]
            else:
                best_version = max(versions, key=lambda v: semver.Version(v['version']))

            return tools.manifest.Manifest(
                name=('%s/%s' % (response['namespace'], response['name'])),
                version=tools.manifest.ComponentVersion(best_version['version']),
                download_url=best_version['url'],
                dependencies=self._version_dependencies(best_version),
                maintainers=None,
            )

        except requests.exceptions.RequestException:
            raise APIClientError('HTTP request error')

        except (ValueError, KeyError, IndexError):
            raise APIClientError('Unexpected component server response')

    def upload_version(self, component_name, file_path):
        if not self.auth_token:
            raise APIClientError('API token is required')

        endpoint = join_url(self.base_url, 'components', component_name.lower(), 'versions')

        with open(file_path, 'rb') as file:
            filename = os.path.basename(file_path)

            encoder = MultipartEncoder({'file': (filename, file, 'application/octet-stream')})
            headers = {'Content-Type': encoder.content_type}
            headers.update(self.auth_header)

            progress_bar = tqdm(total=encoder.len, unit_scale=True, unit='B', disable=None)

            def callback(monitor, memo={'progress': 0}):  # type: (MultipartEncoderMonitor, dict) -> None
                progress_bar.update(monitor.bytes_read - memo['progress'])
                memo['progress'] = monitor.bytes_read

            data = MultipartEncoderMonitor(encoder, callback)

            try:
                response = requests.post(
                    endpoint,
                    data=data,
                    headers=headers,
                )

                response.raise_for_status()
                body = response.json()
                return body['job_id']

            except requests.exceptions.RequestException as e:
                raise APIClientError('Cannot upload version:\n%s' % e)
            finally:
                progress_bar.close()

    def delete_version(self, component_name, component_version):
        endpoint = join_url(self.base_url, 'components', component_name.lower(), component_version)

        if not self.auth_token:
            raise APIClientError('API token is required')

        try:
            response = requests.delete(endpoint, headers=self.auth_header)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise APIClientError('Cannot delete version on the service.\n%s' % e)

    def create_component(self, component_name):
        endpoint = join_url(self.base_url, 'components', component_name.lower())

        if not self.auth_token:
            raise APIClientError('API token is required')

        try:
            response = requests.post(endpoint, headers=self.auth_header)
            response.raise_for_status()
            body = response.json()
            return (body['namespace'], body['name'])

        except requests.exceptions.RequestException as e:
            raise APIClientError('Cannot create new component on the service.\n%s' % e)

    def task_status(self, job_id):  # type: (str) -> TaskStatus
        endpoint = join_url(self.base_url, 'tasks', job_id)

        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            body = response.json()
            return TaskStatus(body['message'], body['status'], body['progress'])

        except requests.exceptions.RequestException as e:
            raise APIClientError('Cannot fetch job status.\n%s' % e)
