# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from integration_tests.integration_test_helpers import project_action


def test_create_project_from_example_path(tmp_path):
    res = project_action(
        str(tmp_path),
        'create-project-from-example',
        '-p',
        str(tmp_path),
        'example/cmp=3.3.8:cmp_ex',
    )

    assert 'successfully downloaded' in res
    assert (tmp_path / 'CMakeLists.txt').is_file()


def test_create_project_from_example_no_path(tmp_path):
    example_name = 'cmp_ex'
    res = project_action(
        str(tmp_path), 'create-project-from-example', 'example/cmp=3.3.8:{}'.format(example_name)
    )

    example_path = tmp_path / example_name
    assert 'successfully downloaded' in res
    assert example_path.is_dir()
    assert (example_path / 'CMakeLists.txt').is_file()


def test_create_project_from_example_project_dir(tmp_path):
    example_name = 'cmp_ex'
    res = project_action(
        str(tmp_path),
        '--project-dir',
        str(tmp_path),
        'create-project-from-example',
        'example/cmp=3.3.8:{}'.format(example_name),
    )

    example_path = tmp_path / example_name
    assert 'successfully downloaded' in res
    assert example_path.is_dir()
    assert (example_path / 'CMakeLists.txt').is_file()
