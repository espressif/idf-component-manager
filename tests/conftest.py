import pytest


@pytest.fixture()
def valid_manifest_hash():
    return '4514062436c2fe6c569710fa3a339a8c5c61281a29e9ef908ddc284d7f3a98f8'


@pytest.fixture()
def valid_manifest():
    return {
        'name': 'test',
        'version': '2.3.1',
        'targets': ['esp32'],
        'maintainers': ['Test Tester <test@example.com>'],
        'description': 'Test project',
        'url': 'https://github.com/espressif/esp-idf',
        'dependencies': {
            'idf': '~4.4.4',
            'test': {
                'version': '>=8.2.0,<9.0.0'
            },
            'test-1': '^1.2.7',
            'test-8': {
                'version': '',
                'public': True,
            },
            'test-2': '',
            'test-4': '*',
            'some_component': {
                'version': '!=1.2.7'
            },
        },
    }
