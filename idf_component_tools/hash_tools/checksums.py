# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json
import os
import typing as t
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from idf_component_tools.hash_tools.calculate import hash_file
from idf_component_tools.utils import BaseModel

from .constants import CHECKSUMS_FILENAME
from .errors import (
    ChecksumsFileNotFound,
    ChecksumsInvalidChecksum,
    ChecksumsInvalidJson,
    ChecksumsUnsupportedAlgorithm,
    ChecksumsUnsupportedVersion,
)


class FileField(BaseModel):
    path: str
    size: int
    hash: str


class ChecksumsModel(BaseModel):
    version: str = '1.0'
    algorithm: str = 'sha256'
    created_at: str = datetime.now(timezone.utc).isoformat()
    files: t.List[FileField] = []


class ChecksumsManager:
    """Class to manage checksums file.

    :param path: Path to the component directory.
    """

    def __init__(self, path: Path):
        self.path = path

    def exists(self) -> bool:
        """Check if checksums file exists.

        :return: True if checksums file exists, False otherwise
        """
        return (self.path / CHECKSUMS_FILENAME).is_file()

    def dump(self) -> None:
        """Writes checksums to a file.

        Format of the file is:

        {
            "version": "1.0",
            "algorithm": "sha256",
            "created_at": "2025-03-14T08:26:00.115229+00:00",
            "files": [
                {
                    "path": "path/to/file",
                    "size": 123,
                    "hash": "b6b4ac12062668b5a36c..."
                },
                ...
            ]
        }
        """

        checksums = ChecksumsModel(
            files=[
                FileField(
                    path=os.path.relpath(file_path, self.path),
                    size=file_path.stat().st_size,
                    hash=hash_file(file_path),
                )
                for file_path in Path(self.path).rglob('*')
                if file_path.is_file()
            ]
        )

        (self.path / CHECKSUMS_FILENAME).write_text(checksums.model_dump_json())

    def load(self) -> ChecksumsModel:
        """Load file with checksums.

        :raises ChecksumsFileNotFound: Checksums file not found
        :raises ChecksumsInvalidJson: Invalid JSON format or validation error
        :raises ChecksumsUnsupportedVersion: Unsupported version
        :raises ChecksumsUnsupportedAlgorithm: Unsupported algorithm
        :raises ChecksumsEmptyFilename: One of filenames is empty
        :raises ChecksumsInvalidChecksum: One of file checksums is invalid
        :return: Loaded checksums model
        """
        # Avoid circular import
        from .validate import is_hash_valid

        path = self.path / CHECKSUMS_FILENAME

        if not path.is_file():
            raise ChecksumsFileNotFound(f'Checksums file not found: {path}')

        try:
            with open(path, 'r', encoding='utf8') as f:
                raw_data = json.load(f)

            checksums = ChecksumsModel(**raw_data)
        except (ValueError, ValidationError):
            raise ChecksumsInvalidJson(f'Invalid checksums file: {path}')

        if checksums.version != '1.0':
            raise ChecksumsUnsupportedVersion(
                f'Unsupported version "{checksums.version}" in: {path}'
            )

        if checksums.algorithm != 'sha256':
            raise ChecksumsUnsupportedAlgorithm(
                f'Unsupported algorithm "{checksums.algorithm}" in: {path}'
            )

        for file in checksums.files:
            if not is_hash_valid(file.hash):
                raise ChecksumsInvalidChecksum(f'Invalid hash of file {file.path} in: {path}')

        return checksums
