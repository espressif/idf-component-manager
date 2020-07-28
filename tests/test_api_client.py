import vcr
from idf_component_tools.api_client import APIClient


class TestAPIClient(object):
    def test_join_url(self):
        tests = [
            {
                'in': ['http://', 'test.com', 'asdfasdf'],
                'out': 'http://test.com/asdfasdf/',
            },
            {
                'in': ['https://test.com:4323/api', 'a/a'],
                'out': 'https://test.com:4323/api/a/a/',
            },
            {
                'in': ['https://test.com:4323/api/', 'a/a/'],
                'out': 'https://test.com:4323/api/a/a/',
            },
            {
                'in': ['', 'a/a/'],
                'out': '/a/a/'
            },
        ]

        for test in tests:
            assert APIClient.join_url(*test['in']) == test['out']

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_component_versions.yaml')
    def test_version(self):
        base_url = 'http://localhost:5000/'
        client = APIClient(base_url=base_url)

        component = client.versions('test/cmp', spec='>=1.0.0')

        assert component.name == 'test/cmp'
        assert len(list(component.versions)) == 2

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_component_details.yaml')
    def test_component(self):
        base_url = 'http://localhost:5000/'
        client = APIClient(base_url=base_url)

        manifest = client.component('test/cmp')

        assert manifest.name == 'test/cmp'
        assert str(manifest.version) == '1.0.1'
