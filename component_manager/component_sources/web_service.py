import os
from hashlib import sha256

import requests

from component_manager.api_client import APIClient

from .base import BaseSource
from .errors import FetchingError

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


class WebServiceSource(BaseSource):
    def __init__(self, source_details=None, download_path=None):
        super(WebServiceSource, self).__init__(source_details)

        self.base_url = source_details.get("service_url", None) or os.getenv(
            "DEFAULT_COMPONENT_SERVICE_URL", "https://components.espressif.com/api/"
        )

        self.api_client = source_details.get("api_client", None) or APIClient(
            base_url=self.base_url
        )

    def name(self):
        return "Web Service"

    @staticmethod
    def known_keys():
        return ["version", "service_url"]

    @property
    def hash_key(self):
        if self._hash_key is None:
            url = urlparse(self.base_url)
            netloc = url.netloc
            path = "/".join(filter(None, url.path.split("/")))
            normalized_path = "/".join([netloc, path])
            self._hash_key = sha256(normalized_path.encode("utf-8")).hexdigest()
        return self._hash_key

    @staticmethod
    def is_me(name, details):
        # This should be run last
        return True

    def versions(self, name, spec):
        return self.api_client.versions(name, spec)

    def unique_path(self, name, details):
        return "~".join([name, details["version"], self.hash_key])

    def fetch(self, name, details):
        version = details.get("version")
        if not version:
            raise FetchingError("Version should provided for %s" % name)

        component = self.api_client.component(name, version)
        url = component.get("url")

        if not url:
            raise FetchingError(
                'Unexpected response: URL wasn\'t found for version %s of "%s"',
                version,
                name,
            )

        file_path = os.path.join(self.download_path, self.filename(name, details))

        with requests.get(url, stream=True, allow_redirects=True) as r:
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        return file_path
