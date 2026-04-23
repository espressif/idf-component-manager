# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import re

import idf_component_tools.build_system_tools as build_system_tools
from idf_component_tools.build_system_tools import CMAKE_PROJECT_LINE, get_idf_version, is_component
from idf_component_tools.manifest import WEB_DEPENDENCY_REGEX


def test_web_dep_re():
    valid_names = {
        'test': ('test', ''),
        't-e-s-t': ('t-e-s-t', ''),
        't-e_s-t': ('t-e_s-t', ''),
        'test>1': ('test', '>1'),
        'test/test>1': ('test/test', '>1'),
        'test/test==2': ('test/test', '==2'),
        't-e-s-t/t_e_s_t*': ('t-e-s-t/t_e_s_t', '*'),
    }

    invalid_names = ('!#@', 'adf\nadsf', '_', '-', '_good')

    for name, groups in valid_names.items():
        assert re.match(WEB_DEPENDENCY_REGEX, name).groups() == groups

    for name in invalid_names:
        assert not re.match(WEB_DEPENDENCY_REGEX, name)


def test_is_component(tmp_path):
    tempdir = str(tmp_path)

    open(os.path.join(tempdir, 'CMakeLists.txt'), 'w').write('\n')
    assert is_component(tmp_path)

    open(os.path.join(tempdir, 'idf_component.yml'), 'w').write('\n')
    assert is_component(tmp_path)


def test_is_not_component(tmp_path):
    tempdir = str(tmp_path)

    # No CMakeLists.txt
    assert not is_component(tmp_path)

    # CMakeLists.txt with CMAKE_PROJECT_LINE is a project
    open(os.path.join(tempdir, 'CMakeLists.txt'), 'w').write(CMAKE_PROJECT_LINE)
    assert not is_component(tmp_path)


def test_get_idf_version_caches_subprocess_result(monkeypatch, tmp_path):
    monkeypatch.delenv('CI_TESTING_IDF_VERSION', raising=False)
    monkeypatch.delenv('IDF_VERSION', raising=False)
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    tools_dir = tmp_path / 'tools'
    tools_dir.mkdir()
    (tools_dir / 'idf.py').write_text('', encoding='utf-8')

    calls = []

    def fake_check_output(args):
        calls.append(args)
        return b'ESP-IDF v5.4.1\n'

    monkeypatch.setattr(build_system_tools.subprocess, 'check_output', fake_check_output)

    assert get_idf_version() == '5.4.1'
    assert get_idf_version() == '5.4.1'
    assert len(calls) == 1


def test_get_idf_version_still_honors_env_override(monkeypatch, tmp_path):
    monkeypatch.delenv('CI_TESTING_IDF_VERSION', raising=False)
    monkeypatch.delenv('IDF_VERSION', raising=False)
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    tools_dir = tmp_path / 'tools'
    tools_dir.mkdir()
    (tools_dir / 'idf.py').write_text('', encoding='utf-8')

    calls = []

    def fake_check_output(args):
        calls.append(args)
        return b'ESP-IDF v5.4.1\n'

    monkeypatch.setattr(build_system_tools.subprocess, 'check_output', fake_check_output)

    assert get_idf_version() == '5.4.1'

    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.5.0')
    assert get_idf_version() == '5.5.0'
    assert len(calls) == 1
