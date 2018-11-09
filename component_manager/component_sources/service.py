import os

from component_manager.api_client import APIClient

from .base import BaseSource


class ServiceSource(BaseSource):
    def __init__(self, source_details=None):
        super(ServiceSource, self).__init__(source_details)
        # TODO: add test
        base_url = source_details.get("service_url", None) or os.getenv(
            "DEFAULT_COMPONENT_SERVICE_URL", "https://components.espressif.com/api/"
        )
        self.api_client = APIClient(base_url=base_url)

    def name(self):
        return "Service"

    @staticmethod
    def known_keys():
        return ["version", "service_url"]

    @staticmethod
    def hash_keys():
        return ["service_url"]

    @staticmethod
    def is_me(name, details):
        # This should be run last
        return True

    def versions(self, name, details):
        return []

    def fetch(self, name, details, components_directory):
        component = self.api_client().component_details("test")
        # TODO: add tests and full implementation
