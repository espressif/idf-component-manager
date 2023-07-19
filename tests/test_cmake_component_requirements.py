# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import filecmp
import os
import shutil

import pytest

from idf_component_manager.cmake_component_requirements import (
    CMakeRequirementsManager,
    ComponentName,
    RequirementsProcessingError,
    check_requirements_name_collisions,
    handle_project_requirements,
)


def test_component_name_without_namespace():
    assert ComponentName('idf', 'some__component').name_without_namespace == 'component'
    assert ComponentName('idf', 'component').name_without_namespace == 'component'


def test_check_requirements_name_collisions_raises():
    reqs = {
        ComponentName('idf', 'ns__cmp'): {},
        ComponentName('idf', 'cmp'): {},
    }

    with pytest.raises(RequirementsProcessingError):
        check_requirements_name_collisions(reqs)


def test_check_requirements_name_collisions_ok():
    reqs = {
        ComponentName('idf', 'ns__cmp'): {},
        ComponentName('idf', 'ns2__cmp'): {},
        ComponentName('idf', 'ns__cmp2'): {},
    }

    check_requirements_name_collisions(reqs)


def test_e2e_cmake_requirements(tmp_path, fixtures_path):
    original_path = os.path.join(fixtures_path, 'component_requires_orig.temp.cmake')
    result_path = os.path.join(str(tmp_path), 'component_requires.temp.cmake')
    shutil.copyfile(original_path, result_path)

    manager = CMakeRequirementsManager(result_path)
    requirements = manager.load()
    name = ComponentName('idf', 'espressif__cmp')
    requirements[name]['PRIV_REQUIRES'].append('abc')
    requirements[name]['REQUIRES'].append('def')
    manager.dump(requirements)

    modified_path = os.path.join(fixtures_path, 'component_requires.temp.cmake')
    assert filecmp.cmp(modified_path, result_path, shallow=False)


def test_handle_project_requirements():
    reqs = {
        ComponentName('idf', 'espressif__cmp'): {
            'REQUIRES': ['a', 'b', 'c'],
            'PRIV_REQUIRES': [],
            '__COMPONENT_REGISTERED': '1',
        },
        ComponentName('idf', 'bmp'): {
            'REQUIRES': ['a', 'b', 'c'],
            'PRIV_REQUIRES': [],
            '__COMPONENT_REGISTERED': '1',
        },
        ComponentName('idf', 'main'): {
            'REQUIRES': ['a', 'b', 'cmp', 'some__bmp'],
            'PRIV_REQUIRES': [],
            '__COMPONENT_REGISTERED': '1',
        },
    }

    handle_project_requirements(reqs)

    assert reqs[ComponentName('idf', 'main')]['REQUIRES'] == ['a', 'b', 'espressif__cmp', 'bmp']
