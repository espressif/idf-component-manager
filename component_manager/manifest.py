"""Classes to work with manifest file"""
import os
import sys
from shutil import copyfile

from strictyaml import YAMLError
from strictyaml import load as load_yaml


class ManifestValidator(object):
    """Validator for manifest object, checks for structure, known fields and valid values"""

    KNOWN_ROOT_DIRECTIVES = (
        "idf-version",
        "maintainer",
        "components",
        "platforms",
        "version",
    )

    def __init__(self, parsed_manifest):
        self.manifest = parsed_manifest
        self._errors = []

    def validate_root_directives(self):
        for directive in self.manifest.keys():
            if directive not in self.KNOWN_ROOT_DIRECTIVES:
                self._errors.append("Unknown root directive: %s" % directive)

        return self

    def validate(self):
        self.validate_root_directives()
        return self._errors


class ManifestParser(object):
    """Parser for manifest file"""

    def __init__(self, path):
        # Path of manifest file
        self._path = path
        self._manifest = None
        self._is_valid = None
        self._validation_errors = []

    def check_filename(self):
        """Check manifest's filename"""
        filename = os.path.basename(self._path)

        if filename != "manifest.yml":
            print(
                "Warning: it's recommended to store your component's list in \"manifest.yml\" at project's root"
            )
        return self

    def init_manifest(self):
        """Lazily create manifest file if it doesn't exist"""
        example_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "manifest_example.yml"
        )

        if not os.path.exists(self._path):
            print("Warning: manifest file wasn't found. Initialize empty manifest")
            copyfile(example_path, self._path)

        return self

    def validate(self):
        validator = ManifestValidator(self.manifest)
        self._validation_errors = validator.validate()
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
    def manifest(self):
        self._manifest = self._manifest or self.parse()
        return self._manifest

    def parse(self):
        with open(self._path, "r") as f:
            try:
                return load_yaml(f.read())
            except YAMLError as e:
                print(
                    "Error: Cannot parse manifest file. Please check that\n\t%s\nis valid YAML file\n"
                    % self._path
                )
                print(e)
                sys.exit(1)

    def prepare(self):
        self.check_filename().init_manifest().validate()

        if not self.is_valid:
            error_count = len(self._validation_errors)
            if error_count == 1:
                print("A problem was found in manifest file:")
            else:
                print("%i problems were found in manifest file:" % error_count)
            for e in self.validation_errors:
                print(e)
            sys.exit(1)

        return self
