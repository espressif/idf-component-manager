# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

import pytest

from .integration_test_helpers import (
    project_action,
)


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_add_dependency(project):
    res = project_action(project, 'add-dependency', 'example/cmp^3.3.8')
    assert 'Successfully added dependency "example/cmp": "^3.3.8" to component "main"' in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_add_dependency_with_path(project):
    path = os.path.join(project, 'project', 'src')
    os.makedirs(path)
    res = project_action(project, 'add-dependency', '--path', path, 'lvgl/lvgl>=8.*')
    assert 'Successfully added dependency "lvgl/lvgl": ">=8.*" to component "src"' in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_add_dependency_with_not_existing_path(project):
    path = os.path.join(project, 'not_existing_path')
    res = project_action(project, 'add-dependency', '--path', path, 'lvgl/lvgl>=8.*')
    assert f'"{path}" directory does not exist.' in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_add_dependency_invalid_dependency(project):
    res = project_action(project, 'add-dependency', '/namespace//component/1.0.0')
    assert (
        'Invalid dependency: "/namespace//component/1.0.0". Please use format "namespace/name".'
        in res
    )


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_add_dependency_invalid_version(project):
    res = project_action(project, 'add-dependency', 'namespace/component>=a.b.c')
    assert 'Invalid dependency version requirement: >=a.b.c. ' in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_add_dependency_invalid_git_url(project):
    res = project_action(
        project,
        'add-dependency',
        '--git',
        'git_url',
        'cmp',
    )
    assert 'Invalid Git remote UR' in res
