import os
import sys
from shutil import copyfile

from strictyaml import YAMLError
from strictyaml import load as load_yaml

from .manifest_validator import ManifestValidator


class ManifestParser(object):
    """Parser for manifest file"""
    def __init__(self, path, component=False):
        # Path of manifest file
        self._is_component = component
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

    def init_manifest(self):
        """Lazily create manifest file if it doesn't exist"""
        if not os.path.exists(self._path):
            example_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'manifest_example.yml')

            print("Info: manifest file wasn't found. Creating project's manifest")
            copyfile(example_path, self._path)

        return self

    def validate(self):
        validator = ManifestValidator(self.manifest_tree)
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
        self._manifest_tree = self._manifest_tree or self.parse_manifest_file()
        return self._manifest_tree

    def parse_manifest_file(self):
        if not os.path.isfile(self._path):
            print('Error: Manifest file does not exist. Please declare valid manifest in: \n\t%s' % self._path)
            sys.exit(1)

        with open(self._path, 'r') as f:
            try:
                return load_yaml(f.read()).data
            except YAMLError as e:
                print('Error: Cannot parse manifest file. Please check that\n\t%s\nis valid YAML file\n' % self._path)
                print(e)
                sys.exit(1)

    def prepare(self, init=False):
        self.check_filename()

        if init:
            self.init_manifest()

        self.validate()

        if not self.is_valid:
            error_count = len(self._validation_errors)
            if error_count == 1:
                print('A problem was found in manifest file:')
            else:
                print('%i problems were found in manifest file:' % error_count)
            for e in self.validation_errors:
                print(e)
            sys.exit(1)

        return self
