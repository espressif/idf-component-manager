# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import pytest

from idf_component_tools.hash_tools.errors import (
    HashDoesNotExistError,
    HashNotEqualError,
    HashNotSHA256Error,
)
from idf_component_tools.hash_tools.validate_managed_component import (
    validate_dir,
    validate_managed_component_by_hashdir,
    validate_managed_component_hash,
)


class TestValidateManagedComponent:
    def test_disabled(self, tmp_path, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_OVERWRITE_MANAGED_COMPONENTS', '1')
        # expect it won't raise exception
        validate_managed_component_hash(str(tmp_path))

    def test_env_overwrite_managed_components_empty(self, tmp_path, monkeypatch):
        # Treated as false
        monkeypatch.setenv('IDF_COMPONENT_OVERWRITE_MANAGED_COMPONENTS', '')
        with pytest.raises(HashDoesNotExistError):
            validate_managed_component_hash(str(tmp_path))

    def test_doesnt_exist(self, tmp_path):
        with pytest.raises(HashDoesNotExistError):
            validate_managed_component_hash(str(tmp_path))

    def test_wrong_format(self, tmp_path):
        (tmp_path / '.component_hash').write_text('wrong_format')
        with pytest.raises(HashNotSHA256Error):
            validate_managed_component_hash(str(tmp_path))

    def test_not_equal(self, tmp_path):
        (tmp_path / '.component_hash').write_text('a' * 64)
        with pytest.raises(HashNotEqualError):
            validate_managed_component_hash(str(tmp_path))

    def test_hash_not_equal(self, hash_component):
        expected_sha = '299e78217cd6cb4f6962dde0de8c34a8aa8df7c80d8ac782d1944a4ec5b0ff8e'

        assert validate_dir(hash_component(1), expected_sha)
        assert validate_dir(
            hash_component(4),
            expected_sha,
            exclude=[
                '**/ignore.dir/*',
                '**/*.me',
            ],
        )
        assert not validate_dir(hash_component(2), expected_sha)
        assert not validate_dir(hash_component(3), expected_sha)
        assert not validate_dir(hash_component(4), expected_sha)

    def test_validate_managed_component_inc_exc_manifest(self, hash_component, tmp_path):
        expected_sha = '299e78217cd6cb4f6962dde0de8c34a8aa8df7c80d8ac782d1944a4ec5b0ff8e'

        assert validate_managed_component_by_hashdir(hash_component(5), expected_sha)
