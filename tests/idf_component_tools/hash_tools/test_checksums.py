# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json

import pytest

from idf_component_tools.hash_tools.checksums import (
    ChecksumsManager,
    ChecksumsModel,
    FileField,
)
from idf_component_tools.hash_tools.constants import CHECKSUMS_FILENAME
from idf_component_tools.hash_tools.errors import (
    ChecksumsFileNotFound,
    ChecksumsInvalidChecksum,
    ChecksumsInvalidJson,
    ChecksumsUnsupportedAlgorithm,
    ChecksumsUnsupportedVersion,
)


def create_file_field(path, size, hash):
    return FileField(
        path=path,
        size=size,
        hash=hash,
    )


def normalize_checksums(checksums):
    del checksums['created_at']
    checksums['files'] = sorted(checksums['files'], key=lambda x: x['path'])
    return checksums


@pytest.fixture
def checksums_model():
    return ChecksumsModel(
        version='1.0',
        algorithm='sha256',
        created_at='2025-03-14T08:26:00.115229+00:00',
        files=[],
    )


def test_checksums_dump(tmp_path, checksums_model):
    component_path = tmp_path / 'component'
    component_path.mkdir()
    (component_path / 'file1.txt').write_text('file1')
    (component_path / 'file2.txt').write_text('file2')
    checksums_manager = ChecksumsManager(component_path)
    checksums_path = component_path / CHECKSUMS_FILENAME

    checksums_model.files.append(
        create_file_field(
            'file1.txt', 5, 'c147efcfc2d7ea666a9e4f5187b115c90903f0fc896a56df9a6ef5d8f3fc9f31'
        )
    )
    checksums_model.files.append(
        create_file_field(
            'file2.txt', 5, '3377870dfeaaa7adf79a374d2702a3fdb13e5e5ea0dd8aa95a802ad39044a92f'
        )
    )

    checksums_manager.dump()
    assert checksums_manager.exists()

    # Normalize checksums for comparison
    stored_checksums = json.loads(checksums_path.read_text())
    expected_checksums = checksums_model.model_dump()

    normalize_checksums(stored_checksums)
    normalize_checksums(expected_checksums)

    assert stored_checksums == expected_checksums


def test_checksums_dump_to_other_path(tmp_path, checksums_model):
    component_path = tmp_path / 'component'
    component_path.mkdir()
    (component_path / 'file1.txt').write_text('file1')
    checksums_manager = ChecksumsManager(component_path)

    checksums_model.files.append(
        create_file_field(
            'file1.txt', 5, 'c147efcfc2d7ea666a9e4f5187b115c90903f0fc896a56df9a6ef5d8f3fc9f31'
        )
    )

    external_path = tmp_path / 'ext'
    external_path.mkdir()
    checksums_path = external_path / CHECKSUMS_FILENAME

    checksums_manager.dump(external_path)
    assert checksums_path.is_file()

    stored_checksums = json.loads(checksums_path.read_text())
    expected_checksums = checksums_model.model_dump()

    normalize_checksums(stored_checksums)
    normalize_checksums(expected_checksums)

    assert stored_checksums == expected_checksums


def test_load_checksums(tmp_path, checksums_model):
    checksums_path = tmp_path / CHECKSUMS_FILENAME
    checksums_manager = ChecksumsManager(tmp_path)

    checksums_model.files.append(
        create_file_field(
            'file1.txt', 5, 'c147efcfc2d7ea666a9e4f5187b115c90903f0fc896a56df9a6ef5d8f3fc9f31'
        )
    )
    checksums_model.files.append(
        create_file_field(
            'file2.txt', 5, '3377870dfeaaa7adf79a374d2702a3fdb13e5e5ea0dd8aa95a802ad39044a92f'
        )
    )

    expected_checksums = checksums_model.model_dump_json()
    checksums_path.write_text(expected_checksums)
    loaded_checksums = checksums_manager.load()
    assert loaded_checksums.model_dump_json() == expected_checksums


def test_load_checksums_no_file(tmp_path):
    checksums_manager = ChecksumsManager(tmp_path)

    with pytest.raises(ChecksumsFileNotFound):
        checksums_manager.load()


def test_load_checksums_invalid_json(tmp_path):
    checksums_path = tmp_path / CHECKSUMS_FILENAME
    checksums_manager = ChecksumsManager(tmp_path)
    checksums_path.write_text('invalid_json')

    with pytest.raises(ChecksumsInvalidJson):
        checksums_manager.load()


def test_load_checksums_invalid_checksums_format(tmp_path):
    checksums_path = tmp_path / CHECKSUMS_FILENAME
    checksums_manager = ChecksumsManager(tmp_path)
    checksums_path.write_text(
        '{"v":111,"algorithm":"sha256","created_at":"2025-03-14T08:26:00.115229+00:00","files":"no files"}'
    )

    with pytest.raises(ChecksumsInvalidJson):
        checksums_manager.load()


def test_load_checksums_unsupported_version(tmp_path, checksums_model):
    checksums_path = tmp_path / CHECKSUMS_FILENAME
    checksums_manager = ChecksumsManager(tmp_path)
    checksums_model.version = '2.0'
    checksums_path.write_text(checksums_model.model_dump_json())

    with pytest.raises(ChecksumsUnsupportedVersion):
        checksums_manager.load()


def test_load_checksums_unsupported_algorithm(tmp_path, checksums_model):
    checksums_path = tmp_path / CHECKSUMS_FILENAME
    checksums_manager = ChecksumsManager(tmp_path)
    checksums_model.algorithm = 'sha1'
    checksums_path.write_text(checksums_model.model_dump_json())

    with pytest.raises(ChecksumsUnsupportedAlgorithm):
        checksums_manager.load()


def test_load_checksums_invalid_hash(tmp_path, checksums_model):
    checksums_path = tmp_path / CHECKSUMS_FILENAME
    checksums_manager = ChecksumsManager(tmp_path)
    checksums_model.files.append(create_file_field('file1.txt', 123, '123'))
    checksums_path.write_text(checksums_model.model_dump_json())

    with pytest.raises(ChecksumsInvalidChecksum):
        checksums_manager.load()
