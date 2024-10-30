# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

import pytest

from .integration_test_helpers import (
    project_action,
)


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_create_manifest(project):
    res = project_action(project, 'create-manifest')
    path = os.path.join(project, 'main', 'idf_component.yml')
    assert f'Created "{path}"' in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_create_manifest_with_path(project):
    res = project_action(project, 'create-manifest', '--path', project)
    path = os.path.join(project, 'idf_component.yml')
    assert f'Created "{path}"' in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_create_manifest_with_not_existing_path(project):
    path = os.path.join(project, 'not_existing_path')
    res = project_action(project, 'create-manifest', '--path', path)
    assert f'"{path}" directory does not exist' in res
