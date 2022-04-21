import pytest
import vcr

from idf_component_manager import version
from idf_component_tools.api_client import APIClient, join_url


@pytest.fixture
def base_url():
    return 'http://localhost:5000'


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
            assert join_url(*test['in']) == test['out']

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_component_versions.yaml')
    def test_version(self, base_url):
        client = APIClient(base_url=base_url)

        # Also check case normalisation
        component = client.versions('Test/Cmp', spec='>=1.0.0')

        assert component.name == 'test/cmp'
        assert len(list(component.versions)) == 2

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_component_details.yaml')
    def test_component(self, base_url):
        client = APIClient(base_url=base_url)

        # Also check case normalisation
        manifest = client.component('tesT/CMP')

        assert manifest.name == 'test/cmp'
        assert str(manifest.version) == '1.0.1'

    def test_user_agent(self, base_url):
        user_agent = APIClient(base_url=base_url).session.headers['user-agent']
        assert user_agent.endswith(str(version))
