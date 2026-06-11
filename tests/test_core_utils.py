# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import pytest
from pytest import raises

from idf_component_manager.core_utils import (
    parse_example,
)
from idf_component_tools.errors import FatalError
from idf_component_tools.file_tools import check_examples_folder


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


def test_parse_example_rejects_colon_in_example_path():
    with raises(FatalError, match='Invalid example path'):
        parse_example('test:component:example', 'test')


def test_parse_example_allows_symbols_and_spaces_in_non_final_segments():
    assert parse_example('test/cmp:tx&st42$ main/example', 'test2') == (
        'test/cmp',
        '*',
        'tx&st42$ main/example',
    )


def test_parse_example_allows_project_name_with_spaces():
    assert parse_example('test/cmp:tx&st42$ main/example name', 'test2') == (
        'test/cmp',
        '*',
        'tx&st42$ main/example name',
    )


def test_parse_example_rejects_reserved_last_path_segment():
    with raises(FatalError, match='Invalid example path'):
        parse_example('test/cmp:tx&st42$ main/CON', 'test2')


def test_check_examples_folder_rejects_reserved_manifest_path_segment(tmp_path):
    (tmp_path / 'CON').mkdir()

    with pytest.raises(FatalError, match='Invalid example path'):
        check_examples_folder([{'path': './CON'}], tmp_path)


def test_check_examples_folder_allows_space_in_project_name(tmp_path):
    (tmp_path / 'folder with space').mkdir()

    check_examples_folder([{'path': './folder with space'}], tmp_path)
