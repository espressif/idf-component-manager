import os
from io import open
from typing import Any, Dict

import yaml

from ..errors import ManifestError
from .validator import ManifestValidator

EMPTY_MANIFEST = dict()  # type: Dict[str, Any]


class ManifestManager(object):
    """Parser for manifest file"""
    def __init__(self, path, is_component=False):
        # Path of manifest file
        self._is_component = is_component
        self._path = path
        self._manifest_tree = None
        self._manifest = None
        self._is_valid = None
        self._validation_errors = []

    def check_filename(self):
        """Check manifest's filename"""
        filename = os.path.basename(self._path)

        if self._is_component and filename != 'idf_component.yml':
            print(
                "Warning: it's recommended to store your component's list in \"idf_component.yml\" at component's root")

        if not self._is_component and filename != 'idf_project.yml':
            print("Warning: it's recommended to store your component's list in \"idf_project.yml\" at project's root")

        return self

    def validate(self):
        validator = ManifestValidator(self.manifest_tree, self._is_component)
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
                return yaml.safe_load(f.read())
            except yaml.YAMLError:
                raise ManifestError(
                    'Cannot parse manifest file. Please check that\n\t%s\nis valid YAML file\n' % self._path)

    def load(self):
        self.check_filename().validate()

        if not self.is_valid:
            error_count = len(self.validation_errors)
            if error_count == 1:
                error_desc = ['A problem was found in manifest file:'] + self.validation_errors
            else:
                error_desc = ['%i problems were found in manifest file:' % error_count] + self.validation_errors

            raise ManifestError('\n'.join(error_desc))

        return self.manifest_tree
