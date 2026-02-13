# SPDX-FileCopyrightText: 2025-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from os import getenv
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from idf_component_tools.semver import Version
from integration_tests.integration_test_helpers import fixtures_path, project_action

idf_version = Version.coerce(getenv('ESP_IDF_VERSION'))


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp': {
                            'override_path': fixtures_path(
                                'components', 'cmp_with_kconfig_var', 'cmp'
                            ),
                        },
                    },
                },
            },
        },
    ],
    indirect=True,
)
def test_prepare_dep_dirs_with_kconfig(project):
    res = project_action(
        project,
        'reconfigure',
    )

    # Count how many times "Processing X dependencies" appears in the output
    # This indicates how many times Component Manager has been run
    processing_count = res.count('NOTICE: Processing')
    assert processing_count == 2

    # Verify that valid Kconfig options are resolved correctly
    lock = YAML().load(Path(project) / 'dependencies.lock')
    assert 'cmp' in lock['dependencies']
    assert 'espressif/esp_codec_dev' in lock['dependencies']
    assert (
        '$CONFIG{ESP_BOARD_DEV_AUDIO_CODEC_SUPPORT} == True'
        in lock['dependencies']['cmp']['dependencies'][0]['matches'][0]['if']
    )
    assert 'service' in lock['dependencies']['espressif/esp_codec_dev']['source']['type']


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp': {
                            'matches': [{'if': '$CONFIG{ADC_ENABLE_DEBUG_LOG} == True'}],
                            'override_path': fixtures_path(
                                'components', 'cmp_with_kconfig_var', 'cmp'
                            ),
                        },
                    },
                },
            },
        },
    ],
    indirect=True,
)
def test_three_runs_cm_kconfig(project):
    (Path(project) / 'sdkconfig').write_text('CONFIG_ADC_ENABLE_DEBUG_LOG=y')

    res = project_action(
        project,
        'reconfigure',
    )

    # Count how many times "Processing X dependencies" appears in the output
    # This indicates how many times Component Manager has been run
    processing_count = res.count('NOTICE: Processing')
    build_system_ver = getenv('IDF_COMPONENT_TESTS_BUILD_SYSTEM_VERSION')
    if build_system_ver == '2':
        # CMake v2 only needs 2 runs of Component Manager, as it generates
        # sdkconfig.json before the first run
        assert processing_count == 2
    else:
        assert processing_count == 3

    assert 'Configuring done' in res
    lock = YAML().load(Path(project) / 'dependencies.lock')
    assert 'cmp' in lock['dependencies']
    assert 'espressif/esp_codec_dev' in lock['dependencies']


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'cmp': {
                            'matches': [{'if': '$CONFIG{ADC} == True'}],
                            'override_path': fixtures_path(
                                'components', 'cmp_with_kconfig_var', 'cmp'
                            ),
                        },
                    },
                },
            },
        },
    ],
    indirect=True,
)
@pytest.mark.xfail(
    getenv('IDF_COMPONENT_TESTS_BUILD_SYSTEM_VERSION') == '2',
    reason='CMakeV2 does not constraint the warning printing from CM',
)
def test_kconfig_warning(project):
    res = project_action(
        project,
        'reconfigure',
    )

    assert res.count('NOTICE: Processing') == 3
    assert res.count('WARNING: The following Kconfig variables were used in "if" clauses') == 1
