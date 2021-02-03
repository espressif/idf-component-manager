import pytest


@pytest.fixture()
def valid_manifest_hash():
    return '4005550d5c500fae5a5ce4555258e92d83bad677e5ab90bb324b94d2c39bdff1'


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
