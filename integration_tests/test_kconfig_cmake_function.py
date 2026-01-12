# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

import pytest

from idf_component_tools.semver.base import Version
from integration_tests.integration_test_helpers import fixtures_path, project_action

idf_version = Version.coerce(os.getenv('ESP_IDF_VERSION'))


@pytest.mark.skipif(
    idf_version < Version.coerce('5.3'),
    reason='KConfig variables in the manifest are not supported in ESP-IDF < 5.3',
)
@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        # This component is Kconfig-gated and depends on cmp_cmake_function
                        'cmp_kconfig_gated': {
                            'matches': [{'if': '$CONFIG{CMP_ENABLE_CMAKE_FUNCTION} == True'}],
                            'override_path': fixtures_path(
                                'components', 'cmp_with_cmake_function', 'cmp_kconfig_gated'
                            ),
                        },
                    },
                },
            },
        },
    ],
    indirect=True,
)
def test_kconfig_gated_cmake_function_dependency(project):
    """
    Test that a Kconfig-gated dependency with a transitive CMake function works on first build.

    This verifies the fix for component ordering during CMake retry when:
    1. main has a Kconfig that defines a config option (in main/Kconfig)
    2. main depends on a component gated by that Kconfig option (cmp_kconfig_gated)
    3. That component has a dependency that provides a CMake function (cmp_cmake_function)
    4. main calls the CMake function from the transitive dependency

    Without the fix, this would fail with "Unknown CMake command" because main
    would be processed before the transitive dependency that provides the function.
    """
    # Add Kconfig to main (defines the config option that gates the dependency)
    main_kconfig = Path(project) / 'main' / 'Kconfig'
    main_kconfig.write_text(
        """menu "Test Configuration"
    config CMP_ENABLE_CMAKE_FUNCTION
        bool "Enable CMake function component"
        default y
endmenu
"""
    )

    # Modify main's CMakeLists.txt to call the CMake function from the transitive dependency
    main_cmake = Path(project) / 'main' / 'CMakeLists.txt'
    main_cmake.write_text(
        """idf_component_register(SRCS "main.c"
                       INCLUDE_DIRS "include")

# Call the CMake function provided by cmp_cmake_function (transitive dependency)
# This will fail if cmp_cmake_function is not processed before main
if(CONFIG_CMP_ENABLE_CMAKE_FUNCTION)
    test_cmake_function_from_component(RESULT_VAR)
    message(STATUS "CMake function result: ${RESULT_VAR}")

    if(NOT RESULT_VAR STREQUAL "CMAKE_FUNCTION_WORKS")
        message(FATAL_ERROR "CMake function did not work correctly!")
    endif()
endif()
"""
    )

    res = project_action(project, 'reconfigure')

    assert 'Unknown CMake command' not in res, f'CMake function not found: {res}'
    assert 'test_cmake_function_from_component was called successfully' in res
    assert 'Configuring done' in res
