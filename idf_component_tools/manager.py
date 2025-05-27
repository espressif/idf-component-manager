# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import enum
import os
import typing as t
from pathlib import Path

from ruamel.yaml import YAML, CommentedMap, YAMLError

from .constants import MANIFEST_FILENAME
from .errors import ManifestError

if t.TYPE_CHECKING:
    from .manifest.models import Manifest


class UploadMode(str, enum.Enum):
    false = 'false'
    component = 'component'
    example = 'example'


class ManifestManager:
    """
    Parser for manifest files in the project.
    """

    def __init__(
        self,
        path: t.Union[str, Path],
        name: str,
        *,
        upload_mode: UploadMode = UploadMode.false,
        # override fields
        version: t.Optional[str] = None,
        repository: t.Optional[str] = None,
        commit_sha: t.Optional[str] = None,
        repository_path: t.Optional[str] = None,
    ) -> None:
        source_path = Path(path)
        self.path: Path = source_path / MANIFEST_FILENAME if source_path.is_dir() else source_path

        self.name = name

        self._manifest: 'Manifest' = None  # type: ignore

        # in upload mode we do more checks
        self.upload_mode = upload_mode

        # overriding fields
        self._version = version
        self._repository = repository
        self._commit_sha = commit_sha
        self._repository_path = repository_path

        # validation attrs
        self._validation_errors: t.List[str] = None  # type: ignore

        self._yaml = YAML()

    def validate(self) -> 'ManifestManager':
        from .manifest.models import (
            Manifest,
            RepositoryInfoField,
            set_validation_context,
        )

        # avoid circular dependency
        from .utils import ComponentVersion

        if self._manifest:
            return self

        if not self.path.exists():
            manifest_dict: t.Dict[str, t.Any] = {}
        # validate manifest
        else:
            try:
                manifest_dict = (
                    self._yaml.load(self.path.read_text(encoding='utf-8')) or CommentedMap()
                )
            except YAMLError:
                self._validation_errors = [
                    'Cannot parse the manifest file. Please check that\n'
                    '\t{}\n'
                    'is a valid YAML file\n'.format(self.path)
                ]
                return self

        if not isinstance(manifest_dict, dict):
            self._validation_errors = [
                'Manifest file should be a dictionary. Please check that\n'
                '\t{}\n'
                'is a valid manifest file\n'.format(self.path)
            ]
            return self

        if self.name:
            manifest_dict['name'] = self.name

        if self._version:
            manifest_dict['version'] = self._version

        manifest_dict['manifest_manager'] = self

        set_validation_context({'upload_mode': self.upload_mode})

        self._validation_errors, self._manifest = Manifest.validate_manifest(  # type: ignore
            manifest_dict,
            upload_mode=self.upload_mode,
            return_with_object=True,
        )

        # override fields defined in manifest manager
        if self._version is not None:
            self._manifest.version = ComponentVersion(self._version)

        if self._repository is not None:
            self._manifest.repository = self._repository

        if self._commit_sha is not None:
            self._manifest.repository_info = RepositoryInfoField.fromdict({
                'commit_sha': self._commit_sha,
                'path': self._repository_path,
            })

        return self

    @property
    def manifest(self) -> 'Manifest':
        if self._manifest is None:
            self.validate()

        return self._manifest

    @property
    def manifest_tree(self) -> t.Dict[str, t.Any]:
        if self._manifest is None:
            self.validate()

        return self._manifest.model_dump()

    @property
    def is_valid(self) -> bool:
        if self._validation_errors is None:
            self.validate()

        return self._validation_errors == []

    @property
    def validation_errors(self) -> t.List[str]:
        if self._validation_errors is None:
            self.validate()

        return self._validation_errors

    def load(self) -> 'Manifest':
        """
        This is the main method to load the manifest file.
        """
        if self.is_valid:
            return self.manifest

        for error in self.validation_errors:
            print(error)

        raise ManifestError('Manifest is not valid')

    def dump(
        self,
        path: t.Optional[t.Union[str, Path]] = None,
    ) -> None:
        if path is None:
            path = self.path

        if os.path.isdir(path):
            path = os.path.join(path, MANIFEST_FILENAME)

        with open(path, 'w', encoding='utf-8') as fw:
            self._yaml.dump(
                self.manifest_tree,
                fw,
            )
