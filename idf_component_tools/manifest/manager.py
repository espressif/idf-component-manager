# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import copy
import os
import typing as t

import yaml

from ..constants import UPDATE_SUGGESTION
from ..errors import ManifestError, MetadataError
from .constants import MANIFEST_FILENAME
from .env_expander import dump_escaped_yaml, expand_env_vars
from .manifest import Manifest
from .metadata import Metadata
from .validator import ExpandedManifestValidator, ManifestValidator

EMPTY_MANIFEST: t.Dict[str, t.Any] = dict()


class ManifestManager:
    """
    Parser for manifest files in the project.

    If expand_environment is True, the manifest file will be parsed
    with environment variables expanded.
    In this case, the dumped manifest file will contain the replaced values.
    """

    def __init__(
        self,
        path: str,  # Path of manifest file
        name: str,
        check_required_fields: bool = False,
        version: t.Optional[str] = None,
        expand_environment: bool = False,
        process_opt_deps: bool = False,
        repository: t.Optional[str] = None,
        commit_sha: t.Optional[str] = None,
        repository_path: t.Optional[str] = None,
    ) -> None:
        # Path of manifest file
        self._path = path
        self._path_checked = False
        self.name = name
        self.version = version
        self.repository = repository
        self.commit_sha = commit_sha
        self.repository_path = repository_path
        self._manifest_tree: t.Optional[t.Dict[str, t.Any]] = None
        self._normalized_manifest_tree: t.Optional[t.Dict[str, t.Any]] = None
        self._manifest = None
        self._is_valid = None
        self._validation_errors: t.List[str] = []
        self.check_required_fields = check_required_fields
        self.expand_environment = expand_environment
        self.process_opt_deps = process_opt_deps
        self._validator = ExpandedManifestValidator if expand_environment else ManifestValidator

    def validate(self):
        try:
            metadata = Metadata.load(self.manifest_tree)
        except MetadataError as e:
            self._validation_errors = e.args
        else:
            validator = self._validator(
                self.manifest_tree,
                check_required_fields=self.check_required_fields,
                metadata=metadata,
            )
            self._validation_errors = validator.validate_normalize()
            self._is_valid = not self._validation_errors
            self._normalized_manifest_tree = copy.deepcopy(validator.manifest_tree)

        return self

    @property
    def is_valid(self):
        if self._is_valid is None:
            self.validate()

        return self._is_valid

    @property
    def validation_errors(self):
        return self._validation_errors

    @property
    def path(self) -> str:
        if self._path_checked:
            return self._path

        if os.path.isdir(self._path):
            self._path = os.path.join(self._path, MANIFEST_FILENAME)
            self._path_checked = True

        return self._path

    def _overwrite_manifest_fields(self, manifest_fields_path: t.Dict) -> None:
        if self._manifest_tree is None:
            return

        for property_name, field_path in manifest_fields_path.items():
            field_name = field_path[-1]
            value = getattr(self, property_name)

            if value is not None:
                subtree: t.Dict[str, t.Any] = self._manifest_tree
                for field in field_path[:-1]:
                    subtree = subtree.setdefault(field, {})
                subtree[field_name] = value

    @property
    def manifest_tree(self):
        if not self._manifest_tree:
            self._manifest_tree = self.parse_manifest_file()
            self._overwrite_manifest_fields({
                'version': ['version'],
                'repository': ['repository'],
                'commit_sha': ['repository_info', 'commit_sha'],
                'repository_path': ['repository_info', 'path'],
            })

        return self._manifest_tree

    @property
    def normalized_manifest_tree(self):
        if not self._normalized_manifest_tree:
            self.validate()

        return self._normalized_manifest_tree

    def exists(self):
        return os.path.isfile(self.path)

    def parse_manifest_file(self) -> t.Dict:
        if not self.exists():
            return EMPTY_MANIFEST

        with open(self.path, encoding='utf-8') as f:
            try:
                manifest_data = yaml.safe_load(f.read())

                if manifest_data is None:
                    manifest_data = EMPTY_MANIFEST

                if self.expand_environment:
                    manifest_data = expand_env_vars(manifest_data)

                if not isinstance(manifest_data, dict):
                    raise ManifestError(f'Unknown format of the manifest file: {self.path}')

                return manifest_data

            except yaml.YAMLError:
                raise ManifestError(
                    'Cannot parse the manifest file. '
                    'Please check that\n\t{}\nis valid YAML file\n'.format(self.path)
                )

    def load(self) -> Manifest:
        self.validate()

        if not self.is_valid:
            error_count = len(self.validation_errors)
            if error_count == 1:
                error_desc = [f'A problem was found in the manifest file {self.path}:']
            else:
                error_desc = [
                    '%i problems were found in the manifest file %s:' % (error_count, self.path)
                ]

            error_desc.extend(self.validation_errors)

            error_desc.append(UPDATE_SUGGESTION)

            raise ManifestError('\n'.join(error_desc))

        for name, details in self.normalized_manifest_tree.get('dependencies', {}).items():
            for opt_deps_key in ['rules', 'matches']:
                if opt_deps_key in details:
                    self.normalized_manifest_tree['dependencies'][name][opt_deps_key] = [
                        opt_dep for opt_dep in details[opt_deps_key]
                    ]

        return Manifest.fromdict(
            self.normalized_manifest_tree, name=self.name, manifest_manager=self
        )

    def dump(self, path: t.Optional[str] = None) -> None:
        if path is None:
            path = self.path

        if os.path.isdir(path):
            path = os.path.join(path, MANIFEST_FILENAME)

        if self.expand_environment:
            dump_escaped_yaml(self.manifest_tree, path)
        else:
            with open(path, 'w', encoding='utf-8') as fw:
                yaml.dump(
                    self.manifest_tree,
                    fw,
                    allow_unicode=True,
                    Dumper=yaml.SafeDumper,
                )
