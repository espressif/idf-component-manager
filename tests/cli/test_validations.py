# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import click
import pytest

from idf_component_manager.cli.validations import (
    validate_add_dependency,
    validate_existing_dir,
    validate_git_url,
    validate_if_archive,
    validate_name,
    validate_path_for_project,
    validate_registry_component,
    validate_sha,
    validate_url,
    validate_url_or_file,
    validate_version,
)

# Group of tests for callbacks used in click options


def test_validate_name():
    assert validate_name(None, None, 'valid') == 'valid'


@pytest.mark.parametrize(
    'invalid_name',
    [
        't',
        't' * 65,
        'тест',
    ],
)
def test_validate_name_invalid_input(invalid_name):
    with pytest.raises(click.BadParameter) as exc_info:
        validate_name(None, None, invalid_name)
    assert 'must be between 2 and 64 characters long' in str(exc_info.value)


def test_validate_existing_dir(tmp_path):
    temp_dir = tmp_path / 'valid_dir'
    temp_dir.mkdir()
    assert validate_existing_dir(None, None, str(temp_dir)) == str(temp_dir)


@pytest.mark.parametrize(
    'invalid_dir',
    [
        '/path/to/nonexistent/dir',  # Non-existent directory
        '',  # Empty path
    ],
)
def test_validate_existing_dir_invalid_input(invalid_dir):
    with pytest.raises(click.BadParameter) as exc_info:
        validate_existing_dir(None, None, invalid_dir)
    assert f'"{invalid_dir}" directory does not exist.' in str(exc_info.value)


def test_validate_url():
    assert validate_url(None, None, 'https://hostname') == 'https://hostname/'


@pytest.mark.parametrize(
    'invalid_url',
    [
        'invalid-url',  # Missing scheme and netloc
        'http://',  # Valid scheme but missing netloc
        'ftp://',  # Unsupported scheme
        'http://:80',  # Valid scheme but no host
        'www.example.com',  # Missing scheme,
    ],
)
def test_validate_url_invalid_input(invalid_url):
    with pytest.raises(click.BadParameter) as exc_info:
        validate_url(None, None, invalid_url)
    assert 'Input should be a valid URL' in str(exc_info.value)


def test_validate_url_or_file():
    assert validate_url_or_file(None, None, 'file:///path/to/file') == 'file:///path/to/file'


@pytest.mark.parametrize(
    'invalid_url',
    [
        'invalid-url',  # Missing scheme
        'http://',  # Valid scheme but missing netloc
        'ftp://',  # Unsupported scheme
    ],
)
def test_validate_url_or_file_invalid_input(invalid_url):
    with pytest.raises(click.BadParameter):
        validate_url_or_file(None, None, invalid_url)


def test_validate_sha():
    assert validate_sha(None, None, 'a' * 40) == 'a' * 40


def test_validate_sha_invalid_input():
    with pytest.raises(click.BadParameter) as exc_info:
        validate_sha(None, None, 'g' * 40)  # non-hexadecimal character
    assert 'Invalid SHA-1 hash.' in str(exc_info.value)


def test_validate_git_url():
    assert (
        validate_git_url(None, None, 'https://github.com/username/repository.git')
        == 'https://github.com/username/repository.git'
    )


def test_validate_git_url_invalid_input():
    with pytest.raises(click.BadParameter) as exc_info:
        validate_git_url(None, None, 'github.com/repo')
    assert 'Invalid Git remote URL.' in str(exc_info.value)


def test_validate_path_for_project(tmp_path):
    temp_dir = tmp_path / 'empty_dir'
    temp_dir.mkdir()
    assert validate_path_for_project(None, None, str(temp_dir)) == str(temp_dir)


def test_validate_path_for_project_is_file(tmp_path):
    temp_file = tmp_path / 'file.txt'
    temp_file.touch()
    with pytest.raises(click.BadParameter) as exc_info:
        validate_path_for_project(None, None, str(temp_file))
    assert 'Your target path is not a directory. ' in str(exc_info.value)


def test_validate_path_for_project_not_empty_directory(tmp_path):
    temp_dir = tmp_path / 'not_empty_directory'
    temp_dir.mkdir()
    (temp_dir / 'file.txt').touch()
    with pytest.raises(click.BadParameter) as exc_info:
        validate_path_for_project(None, None, str(temp_dir))
    assert f'The directory "{str(temp_dir)}" is not empty. ' in str(exc_info.value)


def test_validate_if_archive(tmp_path):
    temp_file = tmp_path / 'file.zip'
    temp_file.touch()
    assert validate_if_archive(None, None, str(temp_file)) == str(temp_file)


@pytest.mark.parametrize(
    'invalid_archive',
    [
        '/path/to/directory',  # Path that is a directory, not a file
        '',  # Empty path
    ],
)
def test_validate_if_archive_not_existing_file(invalid_archive):
    with pytest.raises(click.BadParameter) as exc_info:
        validate_if_archive(None, None, invalid_archive)
    assert f'Cannot find archive to upload: {invalid_archive}' in str(exc_info.value)


def test_validate_if_archive_unknown_extension(tmp_path):
    temp_file = tmp_path / 'file.uknown'
    temp_file.touch()
    with pytest.raises(click.BadParameter) as exc_info:
        validate_if_archive(None, None, str(temp_file))
    assert f'Unknown archive extension for file: {str(temp_file)}' in str(exc_info.value)


def test_validate_version():
    assert validate_version(None, None, '1.2.3') == '1.2.3'


@pytest.mark.parametrize('version', ['1.2', ''])
def test_validate_version_invalid_input(version):
    with pytest.raises(click.BadParameter) as exc_info:
        validate_version(None, None, version)
    assert 'Invalid version scheme.' in str(exc_info.value)


def test_validate_registry_component():
    assert validate_registry_component(None, None, ['namespace/component/1.2.3']) == [
        'namespace/component/1.2.3'
    ]


def test_validate_registry_component_invalid_component():
    with pytest.raises(click.BadParameter) as exc_info:
        validate_registry_component(None, None, ['/namespace//component/1.0.0'])
    assert 'Cannot parse COMPONENT argument. ' in str(exc_info.value)


def test_validate_registry_component_invalid_version():
    with pytest.raises(click.BadParameter) as exc_info:
        validate_registry_component(None, None, ['test/test=1.a'])
    assert 'Invalid version specification:' in str(exc_info.value)


def test_validate_add_dependency():
    ctx = click.Context(click.Command('add-dependency'))
    assert (
        validate_add_dependency(ctx, None, 'namespace/component==1.2.3')
        == 'namespace/component==1.2.3'
    )
    ctx.params = {'git': ''}
    assert validate_add_dependency(ctx, None, 'name') == 'name'


def test_validate_add_dependency_invalid_dependency():
    ctx = click.Context(click.Command('add-dependency'))
    with pytest.raises(click.BadParameter) as exc_info:
        validate_add_dependency(ctx, None, '/namespace//component/1.0.0')
    assert (
        'Invalid dependency: "/namespace//component/1.0.0". Please use format "namespace/name".'
        in str(exc_info.value)
    )


def test_validate_add_dependency_invalid_version():
    ctx = click.Context(click.Command('add-dependency'))
    with pytest.raises(click.BadParameter) as exc_info:
        validate_add_dependency(ctx, None, 'namespace/component>=a.b.c')
    assert 'Invalid dependency version requirement: >=a.b.c. ' in str(exc_info.value)


def test_validate_add_dependency_with_git_empty_name():
    ctx = click.Context(click.Command('add-dependency'))
    ctx.params = {'git': ''}
    with pytest.raises(click.BadParameter) as exc_info:
        validate_add_dependency(ctx, None, '')
    assert 'Name of the dependency can not be an empty string' in str(exc_info.value)
