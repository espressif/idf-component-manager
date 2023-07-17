# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import re

from idf_component_tools.build_system_tools import CMAKE_PROJECT_LINE, is_component
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
