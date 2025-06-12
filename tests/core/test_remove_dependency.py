# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from idf_component_manager.core import remove_dependency_from_project
from idf_component_tools import setup_logging
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import FatalError


def setup_project_description(tmp_path, project_description):
    (tmp_path / 'build').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'build' / 'project_description.json').write_text(
        project_description.format(component_path=str(tmp_path))
    )


def setup_dependency_in_manifest(manifest_path, dependency_name):
    manifest_path = Path(manifest_path)
    manifest_path.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_path / MANIFEST_FILENAME

    yaml = YAML()
    data = yaml.load(manifest_file) if manifest_file.exists() else {}
    data.setdefault('dependencies', {})[dependency_name] = {'version': '1.0.0'}
    yaml.dump(data, manifest_file)


def test_remove_dependency_from_project(tmp_path, project_description, capsys):
    setup_logging()

    setup_project_description(tmp_path, project_description)
    setup_dependency_in_manifest(tmp_path / 'main', 'example/cmp')
    setup_dependency_in_manifest(tmp_path / 'components' / 'joltwallet__littlefs', 'example/cmp')

    remove_dependency_from_project((tmp_path / 'build'), 'example/cmp')

    output = capsys.readouterr().out
    assert 'Successfully removed dependency "example/cmp"' in output
    assert 'main' in output
    assert 'joltwallet__littlefs' in output


def test_not_remove_dependency_from_managed_components(tmp_path, project_description, capsys):
    setup_logging()

    setup_project_description(tmp_path, project_description)
    setup_dependency_in_manifest(tmp_path / 'managed_components' / 'example__cmp', 'example/cmp')

    remove_dependency_from_project((tmp_path / 'build'), 'example/cmp')
    output = capsys.readouterr().out
    assert 'Dependency "example/cmp" not found in any component' in output


def test_not_remove_dependency_from_extra_components(tmp_path, project_description, capsys):
    setup_logging()

    setup_project_description(tmp_path, project_description)
    setup_dependency_in_manifest(tmp_path / 'example__cmp2', 'example/cmp2')

    remove_dependency_from_project((tmp_path / 'build'), 'example/cmp2')
    output = capsys.readouterr().out
    assert 'Dependency "example/cmp2" not found in any component' in output


def test_remove_non_existent_dependency_from_project(tmp_path, project_description, capsys):
    setup_logging()

    setup_project_description(tmp_path, project_description)
    setup_dependency_in_manifest(tmp_path / 'main', 'example/cmp')

    remove_dependency_from_project((tmp_path / 'build'), 'example/cap')

    output = capsys.readouterr().out
    assert 'Dependency "example/cap" not found in any component' in output


def test_remove_dependency_non_existent_project_description():
    with pytest.raises(FatalError, match='Cannot find project description file'):
        remove_dependency_from_project(Path(), '')
