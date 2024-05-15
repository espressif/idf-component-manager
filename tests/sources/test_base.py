# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_tools.sources import Source


class TestValidateBaseSource:
    def test_validate_version_spec_any(self):
        source = Source.from_dependency('test')
        assert source.validate_version_spec('*')
        assert not source.validate_version_spec('***')

    def test_validate_version_spec_semver(self, valid_manifest):
        source = Source.from_dependency('test')
        assert source.validate_version_spec('4.0.1')
        assert not source.validate_version_spec('1.-1.1')
