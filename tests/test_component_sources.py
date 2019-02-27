from component_manager.component_sources import LocalSource, WebServiceSource


class TestComponentWebServiceSource(object):
    EXAMPLE_HASH = "ed55692af0eed2feb68f6d7a2ef95a0142b20518a53a0ceb7c699795359d7dc5"

    def test_service_is_me(self):
        assert WebServiceSource.is_me("test", None)
        assert WebServiceSource.is_me("test", {})
        assert WebServiceSource.is_me("test", {"path": "/"})

    def test_fetch(self):
        source = WebServiceSource(
            source_details={"service_url": "https://example.com/api"},
            download_path="/test/path/",
        )

        assert (
            source.unique_path("cmp", {"version": "1.0.0"})
            == "cmp~1.0.0~%s" % self.EXAMPLE_HASH
        )


class TestComponentLocalSource(object):
    def test_service_is_me(self):
        assert LocalSource.is_me("test", {"path": "/"})
        assert not LocalSource.is_me("test", {"url": "/"})
