# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
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


def test_create_project_from_example_not_empty_path(tmp_path):
    project_path = tmp_path / 'non_empty_dir'
    project_path.mkdir()
    # Add a file to make the directory non-empty
    (project_path / 'example_file.txt').write_text('This is a test file.')

    res = project_action(
        str(tmp_path),
        'create-project-from-example',
        '-p',
        str(project_path),
        'example/cmp=3.3.8:cmp_ex',
    )

    assert (
        f'''Invalid value for '-p' / '--path': The directory "{project_path}" is not empty. '''
        in res
    )


def test_create_project_from_example_path_is_file(tmp_path):
    project_path = tmp_path / 'example_file.txt'
    project_path.write_text('This is a test file.')

    res = project_action(
        str(tmp_path),
        'create-project-from-example',
        '-p',
        str(project_path),
        'example/cmp=3.3.8:cmp_ex',
    )

    assert f'Your target path is not a directory. Please remove the {project_path}' in res


def test_create_project_from_example_no_path(tmp_path):
    example_name = 'cmp_ex'
    res = project_action(
        str(tmp_path), 'create-project-from-example', f'example/cmp=3.3.8:{example_name}'
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
        f'example/cmp=3.3.8:{example_name}',
    )

    example_path = tmp_path / example_name
    assert 'successfully downloaded' in res
    assert example_path.is_dir()
    assert (example_path / 'CMakeLists.txt').is_file()
