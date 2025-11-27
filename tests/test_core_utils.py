# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest
from pytest import raises
from ruamel.yaml import YAML

from idf_component_manager.core_utils import (
    load_project_description_file,
    parse_example,
    try_remove_dependency_from_manifest,
    try_remove_dependency_with_fallback,
    validate_project_description_version,
)
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import FatalError


@pytest.mark.parametrize(
    ('example', 'res'),
    [
        ('test/cmp>=1.0.0:sample_project', ('test/cmp', '>=1.0.0', 'sample_project')),
        ('test/cmp:sample/project', ('test/cmp', '*', 'sample/project')),
        ('cmp:sample/project', ('test2/cmp', '*', 'sample/project')),
        (
            'pre_fix/post-fix^2.1.1~1-pre1:te-xt_me',
            ('pre_fix/post-fix', '^2.1.1~1-pre1', 'te-xt_me'),
        ),
    ],
)
def test_parse_example_valid(example, res):
    assert parse_example(example, 'test2') == res


@pytest.mark.parametrize(
    ('example', 'spec'),
    [
        ('test/cmp>=1.0.0.1:sample_project', '>=1.0.0.1'),
        ('test>=1.1.1/component:example', '>=1.1.1/component'),
        ('test/component>=1.2.2<=1.2.3:example', '>=1.2.2<=1.2.3'),
    ],
)
def test_parse_example_spec_version_error(example, spec):
    with raises(
        FatalError,
        match='Invalid version specification: "{}". Please use format like ">=1" or "*".'.format(
            spec
        ),
    ):
        parse_example(example, 'test')


@pytest.mark.parametrize(
    'example',
    [
        'namespace/test/component:example',
        '/namespace/component:example',
        't@st/component:example',
        'test:component:example',
        'test/component/example',
    ],
)
def test_create_example_name_error(example):
    with raises(
        FatalError,
        match='Cannot parse EXAMPLE argument. '
        'Please use format like: namespace/component=1.0.0:example_name',
    ):
        parse_example(example, 'test')


@pytest.mark.parametrize(
    'dep_to_remove, expected_removed, expected_diff',
    [
        ('test', True, {'test'}),
        ('rest', False, set()),
    ],
)
def test_try_remove_dependency_from_manifest(
    tmp_path, valid_manifest, dep_to_remove, expected_removed, expected_diff
):
    manifest_path = tmp_path / MANIFEST_FILENAME

    with open(manifest_path, 'w') as f:
        YAML().dump(valid_manifest, f)

    was_removed = try_remove_dependency_from_manifest(manifest_path, dep_to_remove)

    with open(manifest_path, 'r') as f:
        manifest = YAML().load(f)

    assert was_removed == expected_removed
    assert set(valid_manifest['dependencies']) - set(manifest['dependencies']) == expected_diff


def test_try_remove_dependency_from_non_existant_manifest():
    with raises(
        FatalError,
        match='Cannot find manifest file at',
    ):
        try_remove_dependency_from_manifest(Path('non_existant_manifest.yaml'), 'test')


def test_load_project_description_file_no_path(tmp_path):
    with pytest.raises(FatalError, match='Cannot find project description file*'):
        load_project_description_file(tmp_path)


def test_load_project_description_file_invalid_json(tmp_path):
    (tmp_path / 'project_description.json').write_text('malformed')

    with pytest.raises(FatalError, match='Invalid JSON in project description file*'):
        load_project_description_file(tmp_path)


def test_load_project_description_file_valid_json(tmp_path):
    (tmp_path / 'project_description.json').write_text('{}')
    load_project_description_file(tmp_path)


def test_validate_project_description_old_version():
    with pytest.raises(
        FatalError,
        match='project_description.json format version 1.2 is not supported.',
    ):
        validate_project_description_version({'version': '1.2'})


def test_validate_project_description_new_version():
    with pytest.raises(
        FatalError,
        match='project_description.json format version 2.0 is not supported.',
    ):
        validate_project_description_version({'version': '2.0'})


def test_validate_project_description_version():
    validate_project_description_version({'version': '1.3'})
    validate_project_description_version({'version': '2.0', 'all_component_info': {}})


def test_try_remove_dependency_with_fallback_no_dir_key():
    with pytest.raises(
        FatalError,
        match='Project description file is missing a required "dir" key*',
    ):
        try_remove_dependency_with_fallback([{}], 'test')


def test_try_remove_dependency_without_fallback(tmp_path):
    (tmp_path / MANIFEST_FILENAME).write_text(
        """
        dependencies:
            test: "*"
        """
    )

    all_component_info = {'test': {'dir': tmp_path, 'source': 'project_components'}}
    paths = try_remove_dependency_with_fallback(all_component_info.values(), 'test')
    assert paths == [(tmp_path / MANIFEST_FILENAME)]


def test_try_remove_dependency_with_fallback(tmp_path):
    (tmp_path / MANIFEST_FILENAME).write_text(
        """
        dependencies:
            espressif/test: "*"
        """
    )

    all_component_info = {'espressif/test': {'dir': tmp_path, 'source': 'project_components'}}
    paths = try_remove_dependency_with_fallback(all_component_info.values(), 'test')
    assert paths == [(tmp_path / MANIFEST_FILENAME)]
