# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import copy
import os
from io import open

import yaml

from ..constants import UPDATE_SUGGESTION
from ..errors import ManifestError, MetadataError
from .constants import MANIFEST_FILENAME
from .env_expander import dump_yaml, expand_env_vars
from .manifest import Manifest
from .metadata import Metadata
from .validator import ManifestValidator

try:
    from typing import Any, Dict, List, Optional
except ImportError:
    pass

EMPTY_MANIFEST = dict()  # type: Dict[str, Any]


def dump_tree(path, manifest_tree):  # type: (str, dict) -> None
    if os.path.isdir(path):
        path = os.path.join(path, MANIFEST_FILENAME)

    dump_yaml(manifest_tree, path)


class ManifestManager(object):
    """Parser for manifest files in the project"""

    def __init__(
        self, path, name, check_required_fields=False, version=None
    ):  # type: (str, str, bool, str | None) -> None
        # Path of manifest file
        self._path = path
        self._path_checked = False
        self.name = name
        self.version = version
        self._manifest_tree = None  # type: Optional[Dict]
        self._normalized_manifest_tree = None  # type: Optional[Dict]
        self._manifest = None
        self._is_valid = None
        self._validation_errors = []  # type: List[str]
        self.check_required_fields = check_required_fields

    def validate(self):
        try:
            metadata = Metadata.load(self.manifest_tree)
        except MetadataError as e:
            self._validation_errors = e.args
        else:
            validator = ManifestValidator(
                self.manifest_tree,
                check_required_fields=self.check_required_fields,
                version=self.version,
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
    def path(self):  # type: () -> str
        if self._path_checked:
            return self._path

        if os.path.isdir(self._path):
            self._path = os.path.join(self._path, MANIFEST_FILENAME)
            self._path_checked = True

        return self._path

    @property
    def manifest_tree(self):
        if not self._manifest_tree:
            self._manifest_tree = self.parse_manifest_file()
            if self.version:
                self._manifest_tree['version'] = self.version

        return self._manifest_tree

    @property
    def normalized_manifest_tree(self):
        if not self._normalized_manifest_tree:
            self.validate()

        return self._normalized_manifest_tree

    def exists(self):
        return os.path.isfile(self.path)

    def parse_manifest_file(self):  # type: () -> Dict
        if not self.exists():
            return EMPTY_MANIFEST

        with open(self.path, mode='r', encoding='utf-8') as f:
            try:
                manifest_data = yaml.safe_load(f.read())

                if manifest_data is None:
                    manifest_data = EMPTY_MANIFEST

                expanded_manifest_data = expand_env_vars(manifest_data)

                if not isinstance(expanded_manifest_data, dict):
                    raise ManifestError('Unknown format of the manifest file: {}'.format(self.path))

                return expanded_manifest_data

            except yaml.YAMLError:
                raise ManifestError(
                    'Cannot parse the manifest file. '
                    'Please check that\n\t{}\nis valid YAML file\n'.format(self.path)
                )

    def load(self):  # type: () -> Manifest
        self.validate()

        if not self.is_valid:
            error_count = len(self.validation_errors)
            if error_count == 1:
                error_desc = ['A problem was found in the manifest file %s:' % self.path]
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

    def dump(self, path=None):  # type: (str | None) -> None
        if path is None:
            path = self.path

        dump_tree(path, self.manifest_tree)
