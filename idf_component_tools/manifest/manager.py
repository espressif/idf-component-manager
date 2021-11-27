import os
from io import open

import yaml

from ..errors import ManifestError
from .constants import MANIFEST_FILENAME
from .manifest import Manifest
from .validator import ManifestValidator

try:
    from typing import Any, Dict, List, Optional
except ImportError:
    pass

EMPTY_MANIFEST = dict()  # type: Dict[str, Any]


class ManifestManager(object):
    """Parser for manifest files in the project"""
    def __init__(
            self, path, name, check_required_fields=False, version=None):  # type: (str, str, bool, str | None) -> None
        # Path of manifest file
        self._path = path
        self.name = name
        self.version = version
        self._manifest_tree = None  # type: Optional[Dict]
        self._manifest = None
        self._is_valid = None
        self._validation_errors = []  # type: List[str]
        self.check_required_fields = check_required_fields

    def check_filename(self):
        """Check manifest's filename"""
        if os.path.isdir(self._path):
            self._path = os.path.join(self._path, MANIFEST_FILENAME)
        return self

    def validate(self):
        validator = ManifestValidator(
            self.manifest_tree, check_required_fields=self.check_required_fields, version=self.version)
        self._validation_errors = validator.validate_normalize()
        self._is_valid = not self._validation_errors
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
    def path(self):
        return self._path

    @property
    def manifest_tree(self):
        if not self._manifest_tree:
            self._manifest_tree = self.parse_manifest_file()

        return self._manifest_tree

    def exists(self):
        return os.path.isfile(self._path)

    def parse_manifest_file(self):  # type: () -> Dict
        if not self.exists():
            return EMPTY_MANIFEST

        with open(self._path, mode='r', encoding='utf-8') as f:
            try:
                manifest_data = yaml.safe_load(f.read())

                if manifest_data is None:
                    manifest_data = EMPTY_MANIFEST

                if not isinstance(manifest_data, dict):
                    raise ManifestError('Unknown format of the manifest file: {}'.format(self._path))

                return manifest_data

            except yaml.YAMLError:
                raise ManifestError(
                    'Cannot parse the manifest file. Please check that\n\t{}\nis valid YAML file\n'.format(self._path))

    def load(self):  # type: () -> Manifest
        self.check_filename().validate()

        if not self.is_valid:
            error_count = len(self.validation_errors)
            if error_count == 1:
                error_desc = ['A problem was found in the manifest file %s:' % self._path] + self.validation_errors
            else:
                error_desc = [
                    '%i problems were found in the manifest file %s:' % (error_count, self._path)
                ] + self.validation_errors

            raise ManifestError('\n'.join(error_desc))

        return Manifest.fromdict(self.manifest_tree, name=self.name)

    def dump(self, path):  # type: (str) -> None
        with open(os.path.join(path, MANIFEST_FILENAME), 'w', encoding='utf-8') as fw:
            yaml.dump(self.manifest_tree, fw)
