# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json
import os

import pytest

from idf_component_tools.build_system_tools import get_idf_version
from idf_component_tools.semver import Version
from integration_tests.integration_test_helpers import project_action


@pytest.mark.skipif(
    Version(get_idf_version()) < Version('5.3.0'), reason='only test it in master branch'
)
@pytest.mark.xfail(reason='not supported yet in ESP-IDF')
class TestComponentTypes:
    @pytest.mark.parametrize(
        'project',
        [
            {
                'root_dependencies': {
                    'example/cmp': {'version': '3.3.9'},
                },
                'components': {
                    'cmp': {},
                    'main': {
                        'dependencies': {
                            'example/cmp': {'version': '3.3.7'},
                        }
                    },
                },
            },
        ],
        indirect=True,
    )
    def test_component_override_priority(self, project):
        res = project_action(project, 'reconfigure')
        assert 'Configuring done' in res

        with open(os.path.join(project, 'build', 'project_description.json')) as fr:
            d = json.load(fr)

        assert 'cmp' in d['build_component_info']
        assert 'example__cmp' not in d['build_component_info']

    @pytest.mark.parametrize(
        'project',
        [
            {
                'root_dependencies': {
                    'hfudev/cmp': {'version': '*'},
                },
                'components': {
                    'main': {
                        'dependencies': {
                            'example/cmp': {'version': '*'},
                        }
                    },
                },
            },
        ],
        indirect=True,
    )
    def test_component_override_priority_with_same_name(self, project):
        res = project_action(project, 'reconfigure')
        assert 'Configuring done' in res
        assert (
            'example__cmp overrides hfudev__cmp since "project_managed_components" type '
            'got higher priority than "idf_components"'
        ) in res

        with open(os.path.join(project, 'build', 'project_description.json')) as fr:
            d = json.load(fr)

        assert 'example__cmp' in d['build_component_info']
        assert 'hfudev__cmp' not in d['build_component_info']

    @pytest.mark.parametrize(
        'project',
        [
            {
                'components': {
                    'main': {
                        'dependencies': {
                            'example/cmp': {'version': '3.3.7'},
                            'hfudev/cmp': {'version': '3.3.8'},
                        }
                    },
                }
            },
        ],
        indirect=True,
    )
    def test_component_override_fail_with_same_component_type(self, project):
        res = project_action(project, 'reconfigure')

        # since the dependency introduced order is not fixed
        assert (
            'Requirement example__cmp and requirement hfudev__cmp '
            'are both added as "project_managed_components"' in res
            or 'Requirement hfudev__cmp and requirement example__cmp '
            'are both added as "project_managed_components"' in res
        )
        assert 'Configuring incomplete, errors occurred!' in res
