import pytest


@pytest.fixture()
def valid_manifest_hash():
    return '7261c3aed4105232f3b832dcfa0e75c2c55f09bd457146f5b6c97c7b55a92af6'


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
                'version': ''
            },
            'test-2': '',
            'test-4': '*',
            'some_component': {
                'version': '!=1.2.7'
            },
        },
    }
