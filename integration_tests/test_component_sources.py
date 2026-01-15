# SPDX-FileCopyrightText: 2023-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import json
import os

import pytest

from integration_tests.integration_test_helpers import project_action


class TestComponentSources:
    @pytest.mark.parametrize(
        'project',
        [
            {
                'components': {
                    'cmp': {},
                    'main': {
                        'dependencies': {
                            'test/cmp': {'version': '*'},
                        }
                    },
                },
            },
        ],
        indirect=True,
    )
    @pytest.mark.xfail(
        os.getenv('IDF_COMPONENT_TESTS_BUILD_SYSTEM_VERSION') == '2',
        reason='Not all discovered components are available during injection in CMake V2',
    )
    def test_component_override_priority_basic(self, project):
        res = project_action(project, 'reconfigure')
        assert 'Configuring done' in res

        assert (
            'cmp overrides test__cmp since "project_components" type '
            'got higher priority than "project_managed_components"'
        ) in res

        with open(os.path.join(project, 'build', 'project_description.json')) as fr:
            d = json.load(fr)

        assert 'cmp' in d['build_component_info']
        assert 'test__cmp' not in d['build_component_info']

    # PACMAN-1207
    # Now the test is skipped because it depend on the functionality implemented in the above MR
    # which is not yet available in the released ESP-IDF versions.
    # `root_dependecies` is a fixture to create root managed components,
    # idf_managed_components (IDF_TOOLS_DIR/root_managed_components/idf<version>/managed_components)
    # but now those components are never used by build system, so the test are not valid.
    @pytest.mark.parametrize(
        'project',
        [
            {
                'root_dependencies': {
                    'example/cmp': {'version': '3.3.9'},
                },
                'components': {
                    'main': {
                        'dependencies': {
                            'test/cmp': {'version': '*'},
                        }
                    },
                },
            },
        ],
        indirect=True,
    )
    @pytest.mark.xfail(reason='not supported yet in ESP-IDF')
    def test_component_override_priority_with_same_name(self, project):
        res = project_action(project, 'reconfigure')
        assert 'Configuring done' in res
        assert (
            'test__cmp overrides example__cmp since "project_managed_components" type '
            'got higher priority than "idf_managed_components"'
        ) in res

        with open(os.path.join(project, 'build', 'project_description.json')) as fr:
            d = json.load(fr)

        assert 'test__cmp' in d['build_component_info']
        assert 'example__cmp' not in d['build_component_info']

    @pytest.mark.parametrize(
        'project',
        [
            {
                'components': {
                    'main': {
                        'dependencies': {
                            'example/cmp': {'version': '3.3.7'},
                            'test/cmp': {'version': '3.3.9~1'},
                        }
                    },
                }
            },
        ],
        indirect=True,
    )
    @pytest.mark.xfail(
        os.getenv('IDF_COMPONENT_TESTS_BUILD_SYSTEM_VERSION') == '2',
        reason='Not all discovered components are available during injection in CMake V2',
    )
    def test_component_override_fail_with_same_component_source(self, project):
        res = project_action(project, 'reconfigure')

        # since the dependency introduced order is not fixed
        assert (
            'Requirement example__cmp and requirement test__cmp '
            'are both added as "project_managed_components"'
            in res
            or 'Requirement test__cmp and requirement example__cmp '
            'are both added as "project_managed_components"'
            in res
        )
        assert 'Configuring incomplete, errors occurred!' in res
