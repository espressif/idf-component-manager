import vcr

from component_manager.api_client import APIClient


class TestAPIClient(object):
    def test_join_url(self):
        tests = [
            {
                "in": ["http://", "test.com", "asdfasdf"],
                "out": "http://test.com/asdfasdf/",
            },
            {
                "in": ["https://test.com:4323/api", "a/a"],
                "out": "https://test.com:4323/api/a/a/",
            },
            {
                "in": ["https://test.com:4323/api/", "a/a/"],
                "out": "https://test.com:4323/api/a/a/",
            },
            {
                "in": ["", "a/a/"],
                "out": "/a/a/"
            },
        ]

        for test in tests:
            assert APIClient.join_url(*test["in"]) == test["out"]

    @vcr.use_cassette("fixtures/vcr_cassettes/test_component_versions.yaml")
    def test_version(self):
        base_url = "http://localhost:8000/api/"
        client = APIClient(base_url=base_url)

        component = client.versions("test", ">=1.0.0")

        assert component.name == "test"
        assert len(list(component.versions)) == 4

    @vcr.use_cassette("fixtures/vcr_cassettes/test_component_details.yaml")
    def test_component(self):
        base_url = "http://localhost:8000/api/"
        client = APIClient(base_url=base_url)

        manifest = client.component("test")

        assert manifest.name == "test"
