# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json
import os
import subprocess
from copy import deepcopy

import jsonschema
import pytest
import vcr
from click.testing import CliRunner
from jsonschema.exceptions import ValidationError

from idf_component_manager.cli.core import initialize_cli
from idf_component_manager.core import ComponentManager
from idf_component_tools.__version__ import __version__
from idf_component_tools.config import Config, ConfigManager
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.file_cache import FileCache
from idf_component_tools.file_tools import directory_size
from idf_component_tools.manager import ManifestManager


def test_raise_exception_on_warnings(monkeypatch):
    # Raises warning in api_client.py in env_cache_time()
    monkeypatch.setenv('IDF_COMPONENT_SERVICE_PROFILE', 'test')

    process = subprocess.Popen(
        [
            'compote',
            '--warnings-as-errors',
            'project',
            'create-from-example',
            'example/cmp=3.3.8:cmp',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _, stderr = process.communicate()
    decoded = stderr.decode('utf-8')

    assert process.returncode == 1
    assert (
        'ERROR: IDF_COMPONENT_SERVICE_PROFILE environment variable is deprecated. '
        'Please use IDF_COMPONENT_REGISTRY_PROFILE instead' in decoded
    )


def test_login_to_registry(monkeypatch, tmp_path, mock_registry, mock_token_information):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    runner = CliRunner()
    cli = initialize_cli()
    output = runner.invoke(
        cli,
        ['registry', 'login', '--no-browser'],
        input='test_token',
        env={'IDF_TOOLS_PATH': str(tmp_path)},
    )

    assert output.exit_code == 0
    # assert that login url is printed
    assert 'http://localhost:5000/settings/tokens?' in output.output
    assert 'Successfully logged in' in output.output


def test_login_with_non_existing_service_profile(
    monkeypatch, tmp_path, mock_registry, mock_token_information
):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    runner = CliRunner()
    cli = initialize_cli()
    output = runner.invoke(
        cli,
        ['registry', 'login', '--no-browser', '--service-profile', 'non-existing'],
        input='test_token',
        env={'IDF_TOOLS_PATH': str(tmp_path)},
    )

    config_content = open(str(tmp_path / 'idf_component_manager.yml')).read()

    assert output.exit_code == 0
    # assert that profile is created with a token
    assert 'non-existing' in config_content


def test_login_deprecated_arguments(monkeypatch, tmp_path, mock_token_information):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    runner = CliRunner()
    cli = initialize_cli()
    output = runner.invoke(
        cli,
        [
            'registry',
            'login',
            '--no-browser',
            '--registry_url',
            'http://localhost:5000',
            '--default_namespace',
            'testspace',
        ],
        input='test_token',
        env={'IDF_TOOLS_PATH': str(tmp_path)},
    )

    config_content = open(str(tmp_path / 'idf_component_manager.yml')).read()

    assert output.exit_code == 0
    # assert that profile is created with provided namespace and registry_url
    assert 'testspace' in config_content
    assert 'http://localhost:5000' in config_content


def test_login_updated_arguments(monkeypatch, tmp_path, mock_token_information):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))

    runner = CliRunner()
    cli = initialize_cli()
    output = runner.invoke(
        cli,
        [
            'registry',
            'login',
            '--no-browser',
            '--registry-url',
            'http://localhost:5000',
            '--default-namespace',
            'testspace',
        ],
        input='test_token',
        env={'IDF_TOOLS_PATH': str(tmp_path)},
    )

    config_content = open(str(tmp_path / 'idf_component_manager.yml')).read()

    assert output.exit_code == 0
    # assert that profile is created with provided namespace and registry_url
    assert 'testspace' in config_content
    assert 'http://localhost:5000' in config_content


def test_logout_from_registry(monkeypatch, tmp_path):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))
    config = Config.fromdict({
        'profiles': {
            'default': {
                'api_token': 'asdf',
            },
        }
    })
    ConfigManager().dump(config)

    runner = CliRunner()
    cli = initialize_cli()
    output = runner.invoke(cli, ['registry', 'logout'], env={'IDF_TOOLS_PATH': str(tmp_path)})

    assert 'Successfully logged out' in output.stdout


def test_create_project_from_example_non_default_registry(mocker):
    mocker.patch('idf_component_manager.core.ComponentManager.create_project_from_example')
    runner = CliRunner()
    cli = initialize_cli()

    runner.invoke(
        cli,
        [
            'project',
            'create-from-example',
            'test/cmp=1.0.0:ex',
            '--service-profile',
            'non-default',
        ],
    )
    ComponentManager.create_project_from_example.assert_called_once_with(
        'test/cmp=1.0.0:ex', path=None, service_profile='non-default'
    )


def test_upload_component_with_invalid_name():
    runner = CliRunner()
    cli = initialize_cli()

    result = runner.invoke(
        cli,
        ['component', 'upload', '--name', 'тест'],
    )

    assert result.exit_code == 2
    assert 'Invalid value for' in result.output


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_manifest_create_add_dependency.yaml')
def test_manifest_create_add_dependency(mock_registry):
    runner = CliRunner()
    with runner.isolated_filesystem() as tempdir:
        os.makedirs(os.path.join(tempdir, 'main'))
        os.makedirs(os.path.join(tempdir, 'components', 'foo'))
        os.makedirs(os.path.join(tempdir, 'src'))
        main_manifest_path = os.path.join(tempdir, 'main', MANIFEST_FILENAME)
        foo_manifest_path = os.path.join(tempdir, 'components', 'foo', MANIFEST_FILENAME)
        # realpath fix for macos: /var is a symlink to /private/var
        # https://stackoverflow.com/questions/12482702/pythons-os-chdir-and-os-getcwd-mismatch-when-using-tempfile-mkdtemp-on-ma
        src_path = os.path.realpath(os.path.join(tempdir, 'src'))
        src_manifest_path = os.path.join(src_path, MANIFEST_FILENAME)

        cli = initialize_cli()

        assert 'Created' in runner.invoke(cli, ['manifest', 'create']).output
        assert 'Created' in runner.invoke(cli, ['manifest', 'create', '--component', 'foo']).output
        assert 'Created' in runner.invoke(cli, ['manifest', 'create', '--path', src_path]).output

        assert (
            runner.invoke(
                cli, ['manifest', 'create', '--component', 'src', '--path', src_path]
            ).exit_code
            == 1
        )
        for filepath in [main_manifest_path, foo_manifest_path]:
            with open(filepath) as file:
                assert file.readline().startswith('## IDF Component Manager')

        assert (
            'Successfully added dependency'
            in runner.invoke(cli, ['manifest', 'add-dependency', 'espressif/cmp']).output
        )
        manifest_manager = ManifestManager(main_manifest_path, 'main')
        assert manifest_manager.manifest_tree['dependencies']['espressif/cmp'] == '*'
        assert (
            'Successfully added dependency'
            in runner.invoke(
                cli,
                ['manifest', 'add-dependency', 'espressif/cmp', '--component', 'foo'],
            ).output
        )
        manifest_manager = ManifestManager(foo_manifest_path, 'foo')
        assert manifest_manager.manifest_tree['dependencies']['espressif/cmp'] == '*'
        assert (
            'Successfully added dependency'
            in runner.invoke(
                cli, ['manifest', 'add-dependency', 'espressif/cmp', '--path', src_path]
            ).output
        )
        manifest_manager = ManifestManager(src_manifest_path, 'src')
        assert manifest_manager.manifest_tree['dependencies']['espressif/cmp'] == '*'


def test_manifest_schema(tmp_path, valid_manifest):
    tempdir = str(tmp_path)

    output = subprocess.check_output(['compote', 'manifest', 'schema'], cwd=tempdir)
    if isinstance(output, bytes):
        output = output.decode('utf8')
    schema_dict = json.loads(output)
    valid_manifest['dependencies']['test']['rules'] = [{'if': 'idf_version < 5'}]
    jsonschema.validate(valid_manifest, schema_dict)

    with pytest.raises(ValidationError, match=r"\[\{'if': 'foo < 5'}]"):
        invalid_manifest = deepcopy(valid_manifest)['dependencies']['test']['rules'] = [
            {'if': 'foo < 5'}
        ]
        jsonschema.validate(invalid_manifest, schema_dict)

    with pytest.raises(ValidationError, match=r'\[1, 2, 3]'):
        invalid_manifest = deepcopy(valid_manifest)['dependencies']['test']['version'] = [1, 2, 3]
        jsonschema.validate(invalid_manifest, schema_dict)

    with pytest.raises(ValidationError, match=r"'1.2.3.pre.1'"):
        invalid_manifest = deepcopy(valid_manifest)['version'] = '1.2.3.pre.1'
        jsonschema.validate(invalid_manifest, schema_dict)

    with pytest.raises(ValidationError, match=r"'test.me'"):
        invalid_manifest = deepcopy(valid_manifest)['url'] = 'test.me'
        jsonschema.validate(invalid_manifest, schema_dict)


def test_cache_clear(monkeypatch, tmp_path, file_with_size):
    cache_path = tmp_path / 'cache'
    monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', str(cache_path))

    cache_path.mkdir()
    file_with_size(cache_path / 'file1.txt', 10)

    output = subprocess.check_output(['compote', 'cache', 'clear'])
    assert directory_size(str(cache_path)) == 0
    assert 'Successfully cleared' in output.decode('utf-8')
    assert str(cache_path) in output.decode('utf-8')


def test_cache_path():
    output = subprocess.check_output(['compote', 'cache', 'path'])
    assert FileCache().path() == output.decode('utf-8').strip()


def test_env_cache_path_empty(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', '')
    output = subprocess.check_output(['compote', 'cache', 'path'])
    assert FileCache().path() == output.decode('utf-8').strip()


def test_cache_size(monkeypatch, tmp_path, file_with_size):
    monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', str(tmp_path))

    file_with_size(tmp_path / 'file1.txt', 14)

    output = subprocess.check_output(['compote', 'cache', 'size'])
    assert '14 bytes' == output.decode('utf-8').strip()

    output = subprocess.check_output(['compote', 'cache', 'size', '--bytes'])
    assert '14' == output.decode('utf-8').strip()


def test_version():
    output = subprocess.check_output(['compote', 'version'])
    assert __version__ in output.decode('utf-8')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata_and_component.yaml')
def test_registry_sync_component_flag(tmp_path, monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')

    manager = ComponentManager(path=str(tmp_path))

    # Subprocess and CliRunner changed to function call, because vcrpy can't handle subprocess,
    # and CliRunner doesn't download component, progress bar stop invoke function.
    manager.sync_registry('default', str(tmp_path / 'test'), 0, ['espressif/test*'], False)

    with open(str(tmp_path / 'test' / 'components' / 'espressif' / 'test.json')) as f:
        data = json.load(f)
    assert len(data['versions']) == 3

    assert (
        len(os.listdir(str(tmp_path / 'test'))) == 5
    )  # 3 versions, 1 dependency and components folder


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata_and_component.yaml')
def test_registry_sync_recursive(tmp_path, mock_registry):
    component_path = tmp_path / 'cmp'
    component_path.mkdir()
    (component_path / 'main').mkdir()

    manager = ComponentManager(path=str(component_path))
    manager.create_manifest()
    manager.add_dependency('espressif/test==1.0.1')
    (component_path / 'main' / 'CMakeLists.txt').write_text('\n')
    manager.path = str(tmp_path)

    # Subprocess and CliRunner changed to function call, because vcrpy can't handle subprocess,
    # and CliRunner doesn't download component, progress bar stop invoke function.
    manager.sync_registry('default', str(tmp_path / 'test'), 0, [], True)

    with open(str(tmp_path / 'test' / 'components' / 'espressif' / 'test.json')) as f:
        data = json.load(f)
    assert len(data['versions']) == 1

    assert len(os.listdir(str(tmp_path / 'test'))) == 2  # 1 version and components folder


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata_and_component.yaml')
def test_registry_sync_one_component(tmp_path, monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')

    component_path = tmp_path / 'cmp'
    component_path.mkdir()
    (component_path / 'main').mkdir()

    manager = ComponentManager(path=str(component_path))
    manager.create_manifest()
    manager.add_dependency('espressif/test==1.0.2')
    (component_path / 'main' / 'CMakeLists.txt').write_text('\n')
    manager.path = str(component_path / 'main')

    # Subprocess and CliRunner changed to function call, because vcrpy can't handle subprocess,
    # and CliRunner doesn't download component, progress bar stop invoke function.
    manager.sync_registry('default', str(tmp_path / 'test'), 0, [], False)

    with open(str(tmp_path / 'test' / 'components' / 'espressif' / 'test.json')) as f:
        data = json.load(f)
    assert len(data['versions']) == 1

    assert (
        len(os.listdir(str(tmp_path / 'test'))) == 3
    )  # 1 version, 1 dependency and components folder
