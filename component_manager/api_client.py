"""Classes to work with Espressif Component Web Service"""
import requests

from .manifest import ComponentVersion, ComponentWithVersions, Manifest


class APIComponentVersion(ComponentVersion):
    def __init__(self, version, url_or_path=None, component_hash=None):
        self.component_hash = component_hash
        self.url_or_path = url_or_path

        super(APIComponentVersion, self).__init__(version)

    def __eq__(self, other):
        return super().__eq__(other) and self.component_hash == other.component_hash


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

        endpoint = self.join_url(self.base_url, 'components', component_name, 'versions')

        try:
            r = requests.get(endpoint, params={'versions': spec})
            response = r.json()

            return ComponentWithVersions(
                name=component_name,
                versions=map(
                    lambda v: APIComponentVersion(
                        version=v['version'],
                        url_or_path=v['url'],
                        component_hash=v.get('hash', None),
                    ),
                    response,
                ),
            )

        except requests.exceptions.RequestException as e:
            # TODO: better display for HTTP/Connection errors
            # TODO: Retry couple times on timeout
            print(e)

        except KeyError:
            print('Unexpected component server response')

    def component(self, component_name, version=None):
        """Manifest for given version of component"""

        endpoint = self.join_url(self.base_url, 'components', component_name)

        try:
            r = requests.get(endpoint)
            response = r.json()

            return Manifest(
                name=response['name'],
                version=ComponentVersion(response['version']),
                maintainers=response['maintainers'],
                url=response['url'],
                # TODO: add dependencies
                dependencies=None,
            )

        except requests.exceptions.RequestException as e:
            # TODO: better display for HTTP/Connection errors
            # TODO: Retry couple times on timeout
            print(e)

        except KeyError:
            print('Unexpected component server response')
