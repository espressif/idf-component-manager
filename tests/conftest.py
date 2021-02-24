import pytest


@pytest.fixture()
def valid_manifest_hash():
    return '3bd35cb477cc57388ff9798b978289aa971d2e1d51e4137d0fa59503c9e50c97'


@pytest.fixture()
def valid_manifest():
    return {
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
        'files': {
            'include': ['**/*'],
            'exclude': ['.pyc']
        }
    }
