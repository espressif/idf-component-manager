# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import pytest

from idf_component_tools.utils import ComponentVersion


class TestComponentVersion:
    def test_comparison(self):
        versions = [
            ComponentVersion('3.0.4'),
            ComponentVersion('3.0.6'),
            ComponentVersion('3.0.5'),
        ]

        assert versions[0] == ComponentVersion('3.0.4')
        assert versions[0] != ComponentVersion('*')
        assert versions[0] != ComponentVersion('699d3202533d13b55df3021d93352d8c242ee81e')
        assert str(max(versions)) == '3.0.6'

    def test_flags(self):
        semver = ComponentVersion('1.2.3')
        assert semver.is_semver
        assert not semver.is_commit_id
        assert not semver.is_any

        semver = ComponentVersion('*')
        assert not semver.is_semver
        assert not semver.is_commit_id
        assert semver.is_any

        semver = ComponentVersion('699d3202533d13b55df3021d93352d8c242ee81e')
        assert not semver.is_semver
        assert semver.is_commit_id
        assert not semver.is_any

    @pytest.mark.parametrize(
        'version, expected',
        [
            ('1.2.3', '1.2.3'),
            ('1.2.3~0', '1.2.3'),
            ('1.2.3~1', '1.2.3~1'),
            ('1.2.3-rc1+build1', '1.2.3-rc1+build1'),
            ('1.2.3~1-rc1+build1', '1.2.3~1-rc1+build1'),
        ],
    )
    def test_string_is_unified(self, version, expected):
        assert str(ComponentVersion(version)) == expected
