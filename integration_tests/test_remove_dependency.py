# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

import pytest

from idf_component_tools.semver import Version

from .integration_test_helpers import project_action

idf_version = Version.coerce(os.getenv('ESP_IDF_VERSION'))


@pytest.mark.xfail(reason='ESP-IDF MR')
@pytest.mark.skipif(
    idf_version < Version.coerce('6.0'),
    reason='remove-dependency is only available with ESP-IDF >= 6.0',
)
@pytest.mark.parametrize(
    'project',
    [{'components': {'main': {'dependencies': {'example/cmp': {'version': '*'}}}}}],
    indirect=True,
)
def test_remove_main_dependency(project):
    res = project_action(project, 'remove-dependency', 'example/cmp')
    assert 'Successfully removed dependency "example/cmp"' in res


@pytest.mark.xfail(reason='ESP-IDF MR')
@pytest.mark.skipif(
    idf_version < Version.coerce('6.0'),
    reason='remove-dependency is only available with ESP-IDF >= 6.0',
)
@pytest.mark.parametrize(
    'project',
    [{'components': {'main': {'dependencies': {'example/cmp': {'version': '*'}}}}}],
    indirect=True,
)
def test_remove_dependency_does_not_exist(project):
    res = project_action(project, 'remove-dependency', 'ns/someabsolutelyoutrageouscomponent')
    assert 'Dependency "ns/someabsolutelyoutrageouscomponent" not found in any component' in res


@pytest.mark.parametrize('project', [{}], indirect=True)
def test_remove_dependency_not_in_old_idf_versions(project):
    res = project_action(project, 'remove-dependency', 'example/cmp')
    if idf_version < Version.coerce('6.0'):
        assert 'command "remove-dependency" is not known to idf.py' in res
    else:
        assert 'Dependency "example/cmp" not found in any component' in res
