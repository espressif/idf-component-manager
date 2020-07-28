"""Classes to work with Espressif Component Web Service"""
import os
from io import open

import idf_component_tools as tools
import requests
import semantic_version as semver


class APIClientError(Exception):
    pass


class APIClient(object):
    def __init__(self, base_url, auth_token=None):
        self.base_url = base_url
        self.auth_token = auth_token

    @staticmethod
    def join_url(*args):
        """
        Joins given arguments into an url and add trailing slash
        """
        parts = list(map(lambda x: x[:-1] if x and x[-1] == '/' else x, args))
        parts.append('')
        return '/'.join(parts)

    # TODO: add some caching to versions and component endpoints
    def versions(self, component_name, spec):
        """List of versions for given component with required spec"""
        endpoint = self.join_url(self.base_url, 'components', component_name)

        try:
            # TODO may be add versions endpoint
            r = requests.get(endpoint)
            response = r.json()

            return tools.manifest.ComponentWithVersions(
                name=component_name,
                versions=map(
                    lambda v: tools.manifest.ComponentVersion(
                        version_string=v['version'], component_hash=v['component_hash']),
                    response['versions'],
                ),
            )

        except requests.exceptions.RequestException:
            # TODO: better display for HTTP/Connection errors
            # TODO: Retry couple times on timeout
            raise APIClientError('HTTP request error')

        except KeyError:
            raise APIClientError('Unexpected component server response')

    def component(self, component_name, version=None):
        """Manifest for given version of component, if version is None most recent version returned"""

        endpoint = self.join_url(self.base_url, 'components', component_name)

        try:
            r = requests.get(endpoint)
            response = r.json()
            versions = response['versions']

            if version:
                requested_version = tools.manifest.ComponentVersion(str(version))
                best_version = list(
                    filter(lambda v: tools.manifest.ComponentVersion(v['version']) == requested_version, versions))[0]
            else:
                best_version = max(versions, key=lambda v: semver.Version(v['version']))

            return tools.manifest.Manifest(
                name=('%s/%s' % (response['namespace'], response['name'])),
                version=tools.manifest.ComponentVersion(best_version['version']),
                download_url=best_version['url'],
                # TODO: add dependencies and maintainers
                dependencies=None,
                maintainers=None,
            )

        except requests.exceptions.RequestException:
            # TODO: better display for HTTP/Connection errors
            # TODO: Retry couple times on timeout
            raise APIClientError('HTTP request error')

        except (ValueError, KeyError, IndexError):
            raise APIClientError('Unexpected component server response')

    def upload_version(self, component_name, file_path):
        endpoint = self.join_url(self.base_url, 'components', component_name, 'versions')
        filename = os.path.basename(file_path)

        files = {'file': (filename, open(file_path, 'rb'), 'application/octet-stream')}

        if not self.auth_token:
            raise APIClientError('API token is required')

        headers = {'Authorization': 'Bearer %s' % self.auth_token}

        try:
            r = requests.post(endpoint, files=files, headers=headers)
            r.raise_for_status()
            response = r.json()
            return response['id']

        except requests.exceptions.RequestException as e:
            raise APIClientError('Cannot upload version:\n%s' % e)
