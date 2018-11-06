"""Classes to work with manifest file"""
import os
import re
import sys
from shutil import copyfile

from semantic_version import Spec, Version
from strictyaml import YAMLError
from strictyaml import load as load_yaml

from .component_sources import SourceBuilder


class Manifest(object):
    def __init__(
        self,
        name=None,
        version=None,
        idf_version=None,
        maintainer=None,
        components=None,
        sources=None,
    ):
        self.name = name
        self.version = version
        self.idf_version = idf_version
        self.maintainer = maintainer
        if components is None:
            components = []
        self.components = components
        if sources is None:
            sources = set()
        self.sources = sources


class Component(object):
    def __init__(self, name, source, version_spec="*"):
        self.version_spec = version_spec
        self.source = source
        self.name = name


class ManifestValidator(object):
    """Validator for manifest object, checks for structure, known fields and valid values"""

    KNOWN_ROOT_KEYS = (
        "idf_version",
        "maintainer",
        "components",
        "platforms",
        "version",
    )

    KNOWN_COMPONENT_KEYS = ("version",)

    KNOWN_PLATFORMS = ("esp32",)

    SLUG_RE = re.compile(r"^[-a-zA-Z0-9_]+\Z")

    def __init__(self, parsed_manifest):
        self.manifest_tree = parsed_manifest
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
        unknown = self._validate_keys(self.manifest_tree, self.KNOWN_ROOT_KEYS)
        if unknown:
            self.add_error("Unknown keys: %s" % ", ".join(unknown))

        return self

    def validate_root_values(self):
        version = self.manifest_tree.get("version", None)
        try:
            if version:
                Version.parse(version)
        except ValueError:
            self.add_error("Project version should be valid semantic version")

        self._validate_version_spec(
            "idf_version", self.manifest_tree.get("idf_version", None)
        )

        return self

    def validate_normalize_components(self):
        if (
            "components" not in self.manifest_tree.keys()
            or not self.manifest_tree["components"]
        ):
            return self

        components = self.manifest_tree["components"]

        # List of components should be a dictionary.
        if not isinstance(components, dict):
            self.add_error(
                'List of components should be a dictionary. For example:\ncomponents:\n  some-component: ">=1.2.3,!=1.2.5"'
            )

            return self

        for component, details in components.items():
            if not self.SLUG_RE.match(component):
                self.add_error(
                    'Component\'s name is not valid "%s", should contain only letters, numbers _ and -.'
                    % component
                )

            if isinstance(details, str):
                components[component] = details = {"version": details}

            if isinstance(details, dict):
                unknown = self._validate_keys(details, self.KNOWN_COMPONENT_KEYS)
                if unknown:
                    self.add_error(
                        'Unknown attributes for component "%s": %s'
                        % (component, ", ".join(unknown))
                    )
                self._validate_version_spec(component, details.get("version", ""))
            else:
                self.add_error(
                    '"%s" version have unknown format. Should be either version string or dictionary with details'
                    % component
                )
                continue

        return self

    def validate_platforms(self):
        platforms = self.manifest_tree.get("platforms", [])

        if isinstance(platforms, str):
            platforms = [platforms]

        if not isinstance(platforms, list):
            self.add_error("Unknown format for list of supported platforms")
            return self

        unknown_platforms = []
        for platform in platforms:
            if platform not in self.KNOWN_PLATFORMS:
                unknown_platforms.append(platform)

        if unknown_platforms:
            self.add_error("Unknown platforms: %s" % ", ".join(unknown_platforms))

        return self

    def validate_normalize(self):
        self.validate_root_keys().validate_root_values().validate_normalize_components().validate_platforms()
        return self._errors


class ManifestPipeline(object):
    """Parser for manifest file"""

    def __init__(self, path):
        # Path of manifest file
        self._path = path
        self._manifest_tree = None
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
        with open(self._path, "r") as f:
            try:
                return load_yaml(f.read()).data
            except YAMLError as e:
                print(
                    "Error: Cannot parse manifest file. Please check that\n\t%s\nis valid YAML file\n"
                    % self._path
                )
                print(e)
                sys.exit(1)

    def build(self):
        tree = self.manifest_tree

        self.manifest = Manifest(
            name=tree.get("name", None), maintainer=tree.get("maintainer", None)
        )

        version = tree.get("version", None)
        if version:
            self.manifest.version = Version(version)

        self.manifest.idf_version = Spec(tree.get("idf_version", None) or "*")

        for name, details in tree.get("components", {}).items():
            source = SourceBuilder(name, details).build()
            self.manifest.sources.add(source)
            component = Component(name, source, version_spec=details["version"])
            self.manifest.components.append(component)

        return self

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
