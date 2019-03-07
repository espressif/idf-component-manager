import os
import shutil
import tempfile

import vcr
from semantic_version import Version

from component_manager.component_sources import LocalSource, WebServiceSource


class TestComponentWebServiceSource(object):
    EXAMPLE_HASH = "ed55692af0eed2feb68f6d7a2ef95a0142b20518a53a0ceb7c699795359d7dc5"
    LOCALHOST_HASH = "1fca862736e33907fa706af6ba0eb960b553aef36cdf60690edb7b0c49a8e96b"

    def test_service_is_me(self):
        assert WebServiceSource.is_me("test", None)
        assert WebServiceSource.is_me("test", {})
        assert WebServiceSource.is_me("test", {"path": "/"})

    def test_unique_path(self):
        source = WebServiceSource(
            source_details={"service_url": "https://example.com/api"},
            download_path="/test/path/",
        )
        assert (
            source.unique_path("cmp", {"version": "1.0.0"})
            == "cmp~1.0.0~%s" % self.EXAMPLE_HASH
        )

    @vcr.use_cassette("fixtures/vcr_cassettes/test_fetch_webservice.yaml")
    def test_fetch(self):
        tempdir = tempfile.mkdtemp()

        try:
            source = WebServiceSource(
                source_details={"service_url": "http://127.0.0.1:8000/api"},
                download_path=tempdir,
            )
            local_path = source.fetch("cmp", {"version": "0.0.1"})

            assert local_path == os.path.join(
                tempdir, "cmp~0.0.1~%s.tgz" % self.LOCALHOST_HASH
            )
            assert os.path.isfile(local_path)

        finally:
            shutil.rmtree(tempdir)


class TestComponentLocalSource(object):
    def test_service_is_me(self):
        assert LocalSource.is_me("test", {"path": "/"})
        assert not LocalSource.is_me("test", {"url": "/"})

    def test_unique_path(self):
        source = LocalSource(
            source_details={"path": os.path.dirname(os.path.realpath(__file__))},
            download_path="/test/path/",
        )
        assert source.unique_path("cmp", {}) == ""

    def test_fetch(self):
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "manifests")
        source = LocalSource(download_path="/test/path/", source_details={"path": path})
        assert source.fetch("cmp", {}).endswith("manifests")

    def test_versions_without_manifest(self):

        tempdir = tempfile.mkdtemp()

        try:
            source = LocalSource(
                source_details={"path": tempdir}, download_path="/test/path/"
            )
            versions = source.versions("test", {})

            assert versions.name == "test"
            assert versions.versions[0].version == Version("0.0.0")

        finally:
            shutil.rmtree(tempdir)

    def test_versions_with_manifest(self):
        path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "..",
            "fixtures",
            "components",
            "cmp",
        )
        source = LocalSource(source_details={"path": path}, download_path="/test/path/")
        versions = source.versions("test", {})

        assert versions.name == "test"
        assert versions.versions[0].version == Version("1.0.0")
