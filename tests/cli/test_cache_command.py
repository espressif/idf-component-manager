# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from idf_component_tools.file_cache import FileCache
from idf_component_tools.file_tools import directory_size


def test_cache_clear(monkeypatch, tmp_path, file_with_size, invoke_cli):
    cache_path = tmp_path / 'cache'
    monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', str(cache_path))

    cache_path.mkdir()
    file_with_size(cache_path / 'file1.txt', 10)

    output = invoke_cli('cache', 'clear').output
    assert directory_size(str(cache_path)) == 0
    assert 'Successfully cleared' in output
    assert str(cache_path) in output


def test_cache_path(invoke_cli):
    output = invoke_cli('cache', 'path').output
    assert FileCache().path() == output.strip()


def test_env_cache_path_empty(monkeypatch, invoke_cli):
    monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', '')
    output = invoke_cli('cache', 'path').output
    assert FileCache().path() == output.strip()


def test_cache_size(monkeypatch, tmp_path, file_with_size, invoke_cli):
    monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', str(tmp_path))

    file_with_size(tmp_path / 'file1.txt', 14)

    output = invoke_cli('cache', 'size').output
    assert '14 bytes' == output.strip()

    output = invoke_cli('cache', 'size', '--bytes').output
    assert '14' == output.strip()
