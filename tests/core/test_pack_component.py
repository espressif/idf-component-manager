# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from idf_component_manager.cli.core import initialize_cli
from idf_component_manager.core import ComponentManager
from idf_component_tools.archive_tools import unpack_archive
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import FatalError, ManifestError
from idf_component_tools.git_client import GitClient
from idf_component_tools.manager import ManifestManager
from idf_component_tools.semver import Version


def list_dir(folder):
    res = []
    for root, _, files in os.walk(folder):
        for file in files:
            res.append(os.path.join(root, file))
    return res


def copy_into(src, dest):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dest, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)


def remove_version_line(path):
    with open(os.path.join(str(path), MANIFEST_FILENAME), 'r+') as f:
        lines = f.readlines()
        f.seek(0)
        f.writelines(lines[1:])
        f.truncate()


def test_pack_component_version_from_CLI_and_not_in_manifest(tmp_path, release_component_path):
    copy_into(release_component_path, str(tmp_path))
    component_manager = ComponentManager(path=str(tmp_path))

    # remove the first version line
    remove_version_line(tmp_path)

    component_manager.pack_component('cmp', '2.3.4')

    tempdir = os.path.join(tempfile.tempdir, 'cmp')
    unpack_archive(os.path.join(component_manager.default_dist_path, 'cmp_2.3.4.tgz'), tempdir)
    manifest = ManifestManager(tempdir, 'cmp').load()
    assert manifest.version == '2.3.4'


def test_pack_component_no_version_provided(tmp_path, release_component_path):
    copy_into(release_component_path, str(tmp_path))
    component_manager = ComponentManager(path=str(tmp_path))

    remove_version_line(tmp_path)

    with pytest.raises(ManifestError, match='Manifest is not valid'):
        component_manager.pack_component('cmp', None)


def test_pack_component_no_version_provided_nor_manifest(tmp_path, release_component_path):
    copy_into(release_component_path, tmp_path)

    component_manager = ComponentManager(path=tmp_path)

    (tmp_path / MANIFEST_FILENAME).unlink()

    with pytest.raises(ManifestError, match='Manifest is not valid'):
        component_manager.pack_component('cmp', None)


def test_pack_component_version_from_git(monkeypatch, tmp_path, pre_release_component_path):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))
    copy_into(pre_release_component_path, str(tmp_path))
    component_manager = ComponentManager(path=str(tmp_path))

    # remove the first version line
    remove_version_line(tmp_path)

    def mock_git_tag(self, cwd=None):  # noqa: ARG001
        return Version('3.0.0')

    monkeypatch.setattr(GitClient, 'get_tag_version', mock_git_tag)

    # Define a destination directory within tmp_path
    dist_dir = tmp_path / 'dist'
    dist_dir.mkdir(parents=True, exist_ok=True)

    runner = CliRunner()
    cli = initialize_cli()
    result = runner.invoke(
        cli,
        [
            'component',
            'pack',
            '--version',
            'git',
            '--name',
            'pre',
            '--dest-dir',
            str(dist_dir),
            '--project-dir',
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0

    tempdir = os.path.join(tempfile.tempdir, 'cmp_pre')

    unpack_archive(os.path.join(component_manager.default_dist_path, 'pre_3.0.0.tgz'), tempdir)
    manifest = ManifestManager(tempdir, 'pre').load()
    assert manifest.version == '3.0.0'
    assert set(list_dir(tempdir)) == set(
        os.path.join(tempdir, file)
        for file in [
            'idf_component.yml',
            'cmp.c',
            'CMakeLists.txt',
            'LICENSE',
            os.path.join('include', 'cmp.h'),
        ]
    )


@pytest.mark.parametrize(
    'version, expected_version',
    [
        ('2.3.4', '2.3.4'),
        ('2.3.4.1', '2.3.4~1'),
        ('2.3.4~1', '2.3.4~1'),
    ],
)
def test_pack_component_with_dest_dir(
    monkeypatch, version, expected_version, tmp_path, release_component_path
):
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tmp_path))
    copy_into(release_component_path, str(tmp_path))

    dest_path = tmp_path / 'dest_dir'
    os.mkdir(str(dest_path))

    # remove the first version line
    remove_version_line(tmp_path)

    runner = CliRunner()
    cli = initialize_cli()
    result = runner.invoke(
        cli,
        [
            'component',
            'pack',
            '--version',
            version,
            '--name',
            'cmp',
            '--dest-dir',
            str(dest_path),
            '--project-dir',
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0

    tempdir = os.path.join(tempfile.tempdir, 'cmp')
    unpack_archive(os.path.join(str(dest_path), 'cmp_{}.tgz'.format(expected_version)), tempdir)
    manifest = ManifestManager(tempdir, 'cmp').load()
    assert manifest.version == expected_version


def test_repack_component_with_dest_dir(tmp_path, release_component_path):
    component_path = tmp_path / 'cmp'
    shutil.copytree(release_component_path, str(component_path))
    component_manager = ComponentManager(path=str(component_path))
    component_name = 'cmp'
    version = '1.0.0'
    dest_dir = 'other_dist'

    component_manager.pack_component(component_name, version, dest_dir)
    component_manager.pack_component(component_name, version, dest_dir)

    unpack_archive(
        str(Path(component_manager.path, dest_dir, 'cmp_1.0.0.tgz')), str(tmp_path / 'unpack')
    )

    assert not (tmp_path / 'unpack' / dest_dir).exists()


def test_pack_component_with_replacing_manifest_params(tmp_path, release_component_path):
    copy_into(release_component_path, str(tmp_path))
    component_manager = ComponentManager(path=str(tmp_path))

    repository_url = 'https://github.com/kumekay/test_multiple_comp'
    commit_id = '252f10c83610ebca1a059c0bae8255eba2f95be4d1d7bcfa89d7248a82d9f111'

    component_manager.pack_component(
        'cmp', '2.3.5', repository=repository_url, commit_sha=commit_id
    )

    tempdir = os.path.join(tempfile.tempdir, 'cmp')
    unpack_archive(os.path.join(component_manager.default_dist_path, 'cmp_2.3.5.tgz'), tempdir)
    manifest = ManifestManager(tempdir, 'cmp').load()

    assert manifest.version == '2.3.5'
    assert manifest.links.repository == repository_url
    assert manifest.repository_info.commit_sha == commit_id


def test_pack_component_with_examples(tmp_path, example_component_path):
    project_path = tmp_path / 'cmp'
    shutil.copytree(example_component_path, str(project_path))
    component_manager = ComponentManager(path=str(project_path))

    component_manager.pack_component('cmp', '2.3.4')

    unpack_archive(
        str(Path(component_manager.default_dist_path, 'cmp_2.3.4.tgz')),
        str(tmp_path / 'unpack'),
    )

    assert (tmp_path / 'unpack' / 'examples' / 'cmp_ex').is_dir()
    assert (
        'cmake_minimum_required(VERSION 3.16)'
        in (tmp_path / 'unpack' / 'examples' / 'cmp_ex' / 'CMakeLists.txt').read_text()
    )


def test_pack_component_with_rules_if(
    tmp_path, release_component_path, valid_optional_dependency_manifest_with_idf
):
    project_path = tmp_path / 'cmp'
    shutil.copytree(release_component_path, str(project_path))
    with open(str(project_path / MANIFEST_FILENAME), 'w') as fw:
        yaml.dump(valid_optional_dependency_manifest_with_idf, fw)

    component_manager = ComponentManager(path=str(project_path))
    component_manager.pack_component('cmp', '2.3.4')


@pytest.mark.parametrize(
    'examples, message',
    [
        (
            [
                {'path': './custom_example_path/cmp_ex'},
                {'path': './custom_example_path_2/cmp_ex'},
            ],
            'Examples from "./custom_example_path/cmp_ex" and "./custom_example_path_2/cmp_ex" '
            'have the same name: cmp_ex.',
        ),
        (
            [{'path': './custom_example_path'}, {'path': './custom_example_path'}],
            'Some paths in the `examples` block in the manifest are listed multiple times: '
            './custom_example_path',
        ),
        ([{'path': './unknown_path'}], "Example directory doesn't exist:*"),
    ],
)
def test_pack_component_with_examples_errors(tmp_path, example_component_path, examples, message):
    project_path = tmp_path / 'cmp'
    shutil.copytree(example_component_path, str(project_path))
    if len(examples) == 2 and examples[0] != examples[1]:  # Add second example
        shutil.copytree(
            str(Path(example_component_path, 'custom_example_path')),
            str(project_path / 'custom_example_path_2'),
        )

    component_manager = ComponentManager(path=str(project_path))

    # Add folder with the same name of the example
    manifest_manager = ManifestManager(project_path, 'cmp')
    manifest_manager.manifest.examples = examples
    manifest_manager.dump(str(project_path))

    with pytest.raises(FatalError, match=message):
        component_manager.pack_component('cmp', '2.3.4')
