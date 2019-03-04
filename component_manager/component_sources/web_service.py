import os
import re
from hashlib import sha256

import requests

from component_manager.api_client import APIClient
from component_manager.utils.archive import ArchiveError, get_format_from_path

from .base import BaseSource
from .errors import FetchingError

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


class WebServiceSource(BaseSource):
    def __init__(self, source_details=None, download_path=None):
        super(WebServiceSource, self).__init__(
            source_details=source_details, download_path=download_path
        )

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
        url = component.url

        if not url:
            raise FetchingError(
                'Unexpected response: URL wasn\'t found for version %s of "%s"',
                version,
                name,
            )

        with requests.get(url, stream=True, allow_redirects=True) as r:

            # Trying to get extension from url
            original_filename = url.split("/")[-1]

            try:
                extension = get_format_from_path(original_filename)[1]
            except ArchiveError:
                extension = None

            # If didn't find anything useful, trying content disposition
            content_disposition = r.headers.get("content-disposition")
            if not extension and content_disposition:
                filenames = re.findall("filename=(.+)", content_disposition)
                try:
                    extension = get_format_from_path(filenames[0])[1]
                except IndexError:
                    raise FetchingError("Web Service returned invalid download url")

            filename = "%s.%s" % (self.unique_path(name, details), extension)

            file_path = os.path.join(self.download_path, filename)

            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

        return file_path
