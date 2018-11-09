from component_manager.component_sources.local import LocalSource
from component_manager.component_sources.service import ServiceSource


class TestComponentServiceSource(object):
    def test_service_is_me(self):
        assert ServiceSource.is_me("test", None)
        assert ServiceSource.is_me("test", {})
        assert ServiceSource.is_me("test", {"path": "/"})


class TestComponentLocalSource(object):
    def test_service_is_me(self):
        assert LocalSource.is_me("test", {"path": "/"})
        assert not LocalSource.is_me("test", {"url": "/"})
