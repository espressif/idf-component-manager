"""Instruments to cache initialized component sources"""
from component_manager.utils.file_cache import FileCache


class SourceCachingProxy(object):
    """Proxy that cache initialised component sources"""

    def __init__(self, cache_root_path=None):
        self.root_path = cache_root_path or FileCache.path()

    def fetch(self, name, details, components_directory):
        pass
