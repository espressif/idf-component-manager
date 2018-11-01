"""Classes to work with manifest file"""
import os
import sys
from shutil import copyfile

from semantic_version import Spec
from strictyaml import YAMLError
from strictyaml import load as load_yaml


class ManifestValidator(object):
    """Validator for manifest object, checks for structure, known fields and valid values"""

    KNOWN_ROOT_KEYS = (
        "idf-version",
        "maintainer",
        "components",
        "platforms",
        "version",
    )

    KNOWN_COMPONENT_KEYS = ("version",)

    KNOWN_PLATFORMS = ("esp32",)

    def __init__(self, parsed_manifest):
        self.manifest = parsed_manifest
        self._errors = []

    @staticmethod
    def _validate_keys(manifest, known_keys):
        unknown_keys = []
        for key in manifest.keys():
            if key not in known_keys:
                unknown_keys.append(key)
        return unknown_keys

    def _validate_version_spec(self, component, spec):
        try:
            Spec.parse(spec or "*")
        except ValueError:
            self.add_error('Version specifications for "%s" are invalid.' % component)

    def add_error(self, message):
        self._errors.append(message)

    def validate_root_keys(self):
        unknown = self._validate_keys(self.manifest, self.KNOWN_ROOT_KEYS)
        if unknown:
            self.add_error("Unknown keys: %s" % ", ".join(unknown))

        return self

    def validate_component_versions(self):
        if "components" not in self.manifest.keys() or not self.manifest["components"]:
            return self

        components = self.manifest["components"]

        # List of components should be a dictionary.
        if not isinstance(components, dict):
            self.add_error(
                'List of components should be a dictionary. For example:\ncomponents:\n  some-component: ">=1.2.3,!=1.2.5"'
            )

            return self

        for component, details in components.items():
            if isinstance(details, dict):
                unknown = self._validate_keys(details, self.KNOWN_COMPONENT_KEYS)
                if unknown:
                    self.add_error(
                        'Unknown attributes for component "%s": %s'
                        % (component, ", ".join(unknown))
                    )
                self._validate_version_spec(component, details.get("version", ""))
            elif isinstance(component, str):
                self._validate_version_spec(component, details)
            else:
                self.add_error(
                    '"%s" version have unknown format. Should be either version string or dictionary with details'
                    % component
                )
                continue

        return self

    def validate(self):
        self.validate_root_keys().validate_component_versions()
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
