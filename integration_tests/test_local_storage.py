# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from textwrap import dedent

from integration_tests.integration_test_helpers import (
    project_action,
)


def test_local_storage_url_argument(tmp_path, fixtures_path):
    mirror_path = fixtures_path / 'partial_mirror'

    # Create empty project
    project_action(str(tmp_path), 'create-project', 'test-project')
    project_path = tmp_path / 'test-project'
    assert project_path.is_dir()

    # Create manifest file with a dependency
    manifest_path = project_path / 'main' / 'idf_component.yml'
    manifest_path.write_text(
        dedent("""\
        dependencies:
            example/cmp: "=3.3.1"
    """)
    )

    # Run reconfigure with default registy URL
    res = project_action(
        project_path,
        'reconfigure',
    )
    assert 'Component "example/cmp" not found' in res

    # Run reconfigure using local mirror
    res = project_action(
        project_path,
        '--local-storage-url',
        f'file://{mirror_path}/',
        'reconfigure',
    )
    assert 'Configuring done' in res
