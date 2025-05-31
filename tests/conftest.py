# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import tempfile
import typing as t
from functools import wraps
from pathlib import Path
from uuid import uuid4

import pytest
import requests_mock
import yaml

from idf_component_manager.core import ComponentManager
from idf_component_tools import HINT_LEVEL, ComponentManagerSettings, get_logger
from idf_component_tools.config import config_file
from idf_component_tools.hash_tools.constants import HASH_FILENAME
from idf_component_tools.registry.api_client import APIClient
from idf_component_tools.registry.api_models import TaskStatus
from idf_component_tools.registry.client_errors import ComponentNotFound, VersionNotFound


@pytest.fixture(scope='session', autouse=True)
def check_network_environment():
    if 'USE_REGISTRY' in os.environ:
        assert os.environ.get('IDF_COMPONENT_REGISTRY_URL'), 'IDF_COMPONENT_REGISTRY_URL is not set'
        assert os.environ.get('IDF_COMPONENT_API_TOKEN'), 'IDF_COMPONENT_API_TOKEN is not set'
        assert os.environ.get('IDF_COMPONENT_STORAGE_URL'), 'IDF_COMPONENT_STORAGE_URL is not set'


def skip_on_real_environment(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # True only if we're not testing with real environment or the test is not marked with 'network'
        not_using_registry = 'USE_REGISTRY' not in os.environ
        test_is_not_marked_network = request.node.get_closest_marker('network') is None
        if not_using_registry or test_is_not_marked_network:
            return func(request, *args, **kwargs)
        return

    return wrapper


@pytest.fixture()
def file_with_size():
    def file_builder(path: t.Union[str, Path], size: int) -> None:
        with open(str(path), 'w') as f:
            f.write('x' * size)

    return file_builder


@pytest.fixture(autouse=True)
def reset_logger():
    yield

    logger = get_logger()
    logger.setLevel(HINT_LEVEL)
    logger.handlers.clear()
    logger.propagate = True


@pytest.fixture(autouse=True)
def monkeypatch_idf_version_and_tools_path(monkeypatch, tmp_path):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.3.0')
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))


@pytest.fixture(autouse=True)
def monkeypatch_disable_request_cache(request, monkeypatch):
    if 'enable_request_cache' in request.keywords:
        return
    monkeypatch.setenv('IDF_COMPONENT_CACHE_HTTP_REQUESTS', '0')


@pytest.fixture()
def valid_manifest():
    return {
        'version': '2.3.1~2',
        'targets': ['esp32'],
        'maintainers': ['Test Tester <test@example.com>'],
        'description': 'Test project',
        'tags': [
            'test_tag',
            'Example',
            'one_more-tag123',
        ],
        'dependencies': {
            'idf': '~4.4.4',
            'test': {'version': '>=8.2.0~1,<9.0.0'},
            'test-1': '^1.2.7',
            'test-8': {
                'version': '*',
                'public': True,
            },
            'test-9': {
                'public': True,
            },
            'test-2': '*',
            'test-4': '*',
            'some_component': {'version': '!=1.2.7'},
        },
        'files': {'include': ['**/*'], 'exclude': ['.pyc']},
        'url': 'https://test.com/homepage',
        'documentation': 'https://test.com/documentation',
        'repository': 'git@github.com:test_project/test.git',
        'issues': 'https://test.com/tracker',
        'discussion': 'https://discuss.com/discuss',
    }


@pytest.fixture
def valid_optional_dependency_manifest(valid_manifest):
    valid_manifest['dependencies']['optional'] = {
        'version': '1.0.0',
        'matches': [
            {
                'if': 'idf_version >= 4.4',
                'version': '2.0.0',
            },
        ],
        'rules': [
            {'if': 'idf_version >= 4.4'},
            {'if': 'target not in [esp32, esp32s2]'},
        ],
    }
    return valid_manifest


@pytest.fixture
def valid_optional_dependency_manifest_with_idf(valid_optional_dependency_manifest, monkeypatch):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.0.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')

    return valid_optional_dependency_manifest


@pytest.fixture()
def tmp_managed_components(tmp_path):
    managed_components_path = tmp_path / 'managed_components'
    managed_components_path.mkdir()

    example_cmp_path = managed_components_path / 'example__cmp'
    example_cmp_path.mkdir()
    example_cmp_hash = example_cmp_path / HASH_FILENAME
    # pragma: allowlist nextline secret
    example_cmp_hash.write_text('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    mag3110_path = managed_components_path / 'mag3110'
    mag3110_path.mkdir()
    mag3110_hash = mag3110_path / HASH_FILENAME
    # pragma: allowlist nextline secret
    mag3110_hash.write_text('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    return str(managed_components_path)


@pytest.fixture(scope='session')
def fixtures_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'fixtures',
    )


@pytest.fixture(scope='session')
def pre_release_component_path(fixtures_path):
    return os.path.join(
        fixtures_path,
        'components',
        'pre',
    )


@pytest.fixture(scope='session')
def release_component_path(fixtures_path):
    return os.path.join(
        fixtures_path,
        'components',
        'cmp',
    )


@pytest.fixture(scope='session')
def cmp_with_example(fixtures_path):
    return os.path.join(
        fixtures_path,
        'components',
        'cmp_with_example',
    )


@pytest.fixture(scope='session')
def example_component_path(fixtures_path):
    return os.path.join(
        fixtures_path,
        'components',
        'cmp_for_examples',
    )


@pytest.fixture(scope='function', autouse=True)
def disable_local_env(request):
    if 'network' in request.keywords:
        yield
        return

    restore_env = {}
    for name in ComponentManagerSettings.known_env_vars():
        restore_env[name] = os.environ.pop(name, None)

    yield

    for name, value in restore_env.items():
        if value is not None:
            os.environ[name] = value


@pytest.fixture()
@skip_on_real_environment
def mock_registry_without_token(request, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')


@pytest.fixture()
@skip_on_real_environment
def mock_storage(request, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', 'http://localhost:9000/test-public/')


@pytest.fixture()
@skip_on_real_environment
def mock_registry(request, mock_registry_without_token, mock_storage):
    pass


@pytest.fixture()
@skip_on_real_environment
def mock_yank(request, monkeypatch):  # noqa: ARG001
    monkeypatch.setattr(APIClient, 'yank_version', lambda *_, **__: None)


@pytest.fixture()
@skip_on_real_environment
def mock_yank_404(request, monkeypatch):  # noqa: ARG001
    def f(*_, **__):
        raise VersionNotFound('Version "1.2.0" of component "cmp" was not found in the registry.')

    monkeypatch.setattr(APIClient, 'yank_version', f)


@pytest.fixture()
@skip_on_real_environment
def mock_upload(request, monkeypatch):  # noqa: ARG001
    task_status = TaskStatus(id='id', status='success', warnings=[])
    monkeypatch.setattr(APIClient, 'upload_version', lambda *_, **__: 'job_id')
    monkeypatch.setattr(APIClient, 'task_status', lambda *_, **__: task_status)


@pytest.fixture
def mock_token_information():
    with requests_mock.Mocker() as m:
        m.get(
            'http://localhost:5000/api/tokens/current',
            json={
                'id': '123',
                'description': 'test token',
                'created_at': '2022-01-01T00:00:00Z',
                'expires_at': None,
                'scope': 'user',
                'access_token_prefix': 'abc123',
            },
        )
        yield m


@pytest.fixture
def hash_component(fixtures_path):
    def inner(id):
        return os.path.join(
            fixtures_path,
            'hash_examples',
            f'component_{id}',
        )

    return inner


def upload_cmp_1_0_0():
    manifest = {
        'description': 'This component is an example, to be used for testing.',
        'url': 'https://github.com/somewhere_over_the_rainbow',
        'dependencies': {
            'idf': '>=4.4.0',
            'test_component_manager/dep': {
                'version': '==1.0.0',
                'registry_url': f'{os.environ["IDF_COMPONENT_REGISTRY_URL"]}',
            },
        },
    }
    upload_test_component('cmp', manifest, '1.0.0')


def upload_cmp_1_0_1():
    manifest = {
        'description': 'This component is an example, to be used for testing.',
        'url': 'https://github.com/somewhere_over_the_rainbow',
        'dependencies': {
            'idf': '>=4.4.0',
            'test_component_manager/dep': {
                'version': '<=1.0.1',
                'registry_url': f'{os.environ["IDF_COMPONENT_REGISTRY_URL"]}',
            },
        },
    }
    upload_test_component('cmp', manifest, '1.0.1')


def upload_cmp_2_0_0_alpha1():
    manifest = {
        'description': 'This component is an example, to be used for testing.',
        'url': 'https://github.com/somewhere_over_the_rainbow',
        'dependencies': {
            'idf': '>=4.4.0',
        },
    }
    upload_test_component('cmp', manifest, '2.0.0-alpha1')


def upload_dep_1_0_0():
    manifest = {
        'description': 'This component is a dependency for cmp, to be used for testing.',
        'url': 'https://github.com/somewhere_over_the_rainbow',
        'targets': ['esp32'],
    }
    upload_test_component('dep', manifest, '1.0.0')


def upload_dep_1_0_1():
    manifest = {
        'description': 'This component is a dependency for cmp, to be used for testing.',
        'url': 'https://github.com/somewhere_over_the_rainbow',
        'targets': ['esp32'],
    }

    upload_test_component('dep', manifest, '1.0.1')


def upload_only_pre_release():
    manifest = {
        'description': 'This component is a pre-release example, to be used for testing.',
        'url': 'https://github.com/somewhere_over_the_rainbow',
        'targets': ['esp32'],
    }
    upload_test_component('pre', manifest, '0.0.5-alpha1')


def upload_test_component(component_name, manifest, version, yank=False):
    """
    Helper function to upload a component to the registry
    for testing purposes with the real environment
    """
    with tempfile.TemporaryDirectory() as tmp_path:
        fixtures_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'fixtures',
        )
        cmp_path = Path(fixtures_path) / 'components' / 'cmp_with_example'
        # Copy the component to the temporary directory
        temp_cmp_path = Path(tmp_path) / component_name
        shutil.copytree(cmp_path, temp_cmp_path)
        # Replace the manifest file with the provided dictionary
        if manifest:
            manifest_path = temp_cmp_path / 'idf_component.yml'
            with open(manifest_path, 'w') as fw:
                yaml.dump(manifest, fw)
        # Upload the component to the registry
        manager = ComponentManager(path=temp_cmp_path)
        manager.upload_component(component_name, version, namespace='test_component_manager')
        if yank:
            while True:
                try:
                    manager.yank_version(
                        component_name,
                        version,
                        'Yanking a test version',
                        namespace='test_component_manager',
                    )
                    break
                except Exception:
                    pass


def disable_request_cache(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        request_caching = os.environ.get('IDF_COMPONENT_CACHE_HTTP_REQUESTS')
        try:
            os.environ['IDF_COMPONENT_CACHE_HTTP_REQUESTS'] = '0'
            return func(*args, **kwargs)
        finally:
            if request_caching is not None:
                os.environ['IDF_COMPONENT_CACHE_HTTP_REQUESTS'] = request_caching
            else:
                os.environ.pop('IDF_COMPONENT_CACHE_HTTP_REQUESTS', None)

    return wrapper


@pytest.fixture(scope='session', autouse=True)
@disable_request_cache
def check_and_upload_components_for_testing():
    if 'USE_REGISTRY' not in os.environ:
        return

    api_client = APIClient(
        registry_url=os.environ.get('IDF_COMPONENT_REGISTRY_URL'),
        api_token=os.environ.get('IDF_COMPONENT_API_TOKEN'),
        default_namespace='test_component_manager',
    )

    try:
        api_client.versions('test_component_manager/dep', spec='*')
    except ComponentNotFound:
        upload_dep_1_0_0()
        upload_dep_1_0_1()

    try:
        api_client.versions('test_component_manager/cmp', spec='*')
    except ComponentNotFound:
        upload_cmp_1_0_0()
        upload_cmp_1_0_1()
        upload_cmp_2_0_0_alpha1()

    try:
        api_client.versions('test_component_manager/pre', spec='*')
    except ComponentNotFound:
        upload_only_pre_release()

    try:
        api_client.versions('test_component_manager/ynk', spec='*')
    except ComponentNotFound:
        upload_test_component('ynk', None, '1.0.0', yank=True)

    try:
        api_client.versions('test_component_manager/stb_and_ynk', spec='*')
    except ComponentNotFound:
        upload_test_component('stb_and_ynk', None, '1.0.0', yank=True)
        upload_test_component('stb_and_ynk', None, '1.0.1')

    try:
        api_client.versions('test_component_manager/pre_and_ynk', spec='*')
    except ComponentNotFound:
        upload_test_component('pre_and_ynk', None, '1.0.0', yank=True)
        upload_test_component('pre_and_ynk', None, '2.0.0-alpha1')

    try:
        api_client.versions('test_component_manager/stb_and_ynk_and_pre', spec='*')
    except ComponentNotFound:
        upload_test_component('stb_and_ynk_and_pre', None, '1.0.0', True)
        upload_test_component('stb_and_ynk_and_pre', None, '1.0.1')
        upload_test_component('stb_and_ynk_and_pre', None, '2.0.0-alpha1')

    try:
        api_client.versions('test_component_manager/test_yankable', spec='*')
    except ComponentNotFound:
        upload_test_component('test_yankable', None, '1.0.0')


@pytest.fixture(scope='function')
def component_name():
    if 'USE_REGISTRY' in os.environ:
        return f'test_{str(uuid4())}'
    return 'test'


@pytest.fixture
def isolate_idf_component_manager_yml(tmp_path):
    config_path = config_file()
    backup_path = tmp_path / 'idf_component_manager.yml'

    do_exist = config_path.is_file()
    if do_exist:
        shutil.move(config_path, backup_path)
        yield
        shutil.move(backup_path, config_path)
    else:
        yield
        try:
            config_path.unlink()
        except FileNotFoundError:
            pass
