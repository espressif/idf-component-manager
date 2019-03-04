"""Classes to work with Espressif Component Web Service"""
import requests
from semantic_version import Version

from .manifest import Manifest


class ComponentVersion(object):
    def __init__(self, version, url):
        self.version = version if isinstance(version, Version) else Version(version)
        self.url = url


class Component(object):
    def __init__(self, name, versions):
        self.versions = versions
        self.name = name.lower()  # Use only lower-case names internally


class APIClient(object):
    def __init__(self, base_url, auth_token=None):
        self.base_url = base_url
        self.auth_token = auth_token

    @staticmethod
    def join_url(*args):
        """
        Joins given arguments into an url and add trailing slash
        """
        parts = list(map(lambda x: x[:-1] if x and x[-1] == "/" else x, args))
        parts.append("")
        return "/".join(parts)

    def versions(self, component_name, spec):
        """List of versions for given component with required spec"""

        endpoint = self.join_url(
            self.base_url, "components", component_name, "versions"
        )

        try:
            r = requests.get(endpoint, params={"versions": spec})
            response = r.json()

            # TODO: cleanup interface use same classes as in manifest.py
            return Component(
                name=component_name,
                versions=map(
                    lambda v: ComponentVersion(version=v["version"], url=v["url"]),
                    response,
                ),
            )

        except requests.exceptions.RequestException as e:
            # TODO: better display for HTTP/Connection errors
            # TODO: Retry couple times on timeout
            print(e)

        except KeyError:
            print("Unexpected component server response")

    def component(self, component_name, version=None):
        """Manifest for given version of component"""

        endpoint = self.join_url(self.base_url, "components", component_name)

        try:
            r = requests.get(endpoint)
            response = r.json()

            return Manifest(
                name=response["name"],
                version=Version(response["version"]),
                maintainers=response["maintainers"],
                url=response["url"],
                # TODO: add dependencies
                dependencies=None,
            )

        except requests.exceptions.RequestException as e:
            # TODO: better display for HTTP/Connection errors
            # TODO: Retry couple times on timeout
            print(e)

        except KeyError:
            print("Unexpected component server response")
