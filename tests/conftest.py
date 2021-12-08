import pytest


@pytest.fixture()
def valid_manifest_hash():
    return '4daaa65faaa56fc0db508e3777072ed8f45feb639d5584c327ce212e94861cc6'


@pytest.fixture()
def valid_manifest():
    return {
        'version': '2.3.1',
        'targets': ['esp32'],
        'maintainers': ['Test Tester <test@example.com>'],
        'description': 'Test project',
        'url': 'https://github.com/espressif/esp-idf',
        'tags': [
            'test_tag',
            'Example',
            'one_more-tag123',
        ],
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
