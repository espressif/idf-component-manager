import re

from semantic_version import Spec, Version


class ManifestValidator(object):
    """Validator for manifest object, checks for structure, known fields and valid values"""

    KNOWN_ROOT_KEYS = ("maintainers", "dependencies", "targets", "version", "name")

    KNOWN_COMPONENT_KEYS = ("version", )

    KNOWN_PLATFORMS = ("esp32", )

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

        return self

    def validate_normalize_dependencies(self):
        if ("dependencies" not in self.manifest_tree.keys() or not self.manifest_tree["dependencies"]):
            return self

        dependencies = self.manifest_tree["dependencies"]

        # List of components should be a dictionary.
        if not isinstance(dependencies, dict):
            self.add_error('List of dependencies should be a dictionary.' +
                           ' For example:\ndependencies:\n  some-component: ">=1.2.3,!=1.2.5"')

            return self

        for component, details in dependencies.items():
            if not self.SLUG_RE.match(component):
                self.add_error('Component\'s name is not valid "%s", should contain only letters, numbers _ and -.' %
                               component)

            if isinstance(details, str):
                dependencies[component] = details = {"version": details}

            if isinstance(details, dict):
                unknown = self._validate_keys(details, self.KNOWN_COMPONENT_KEYS)
                if unknown:
                    self.add_error('Unknown attributes for component "%s": %s' % (component, ", ".join(unknown)))
                self._validate_version_spec(component, details.get("version", ""))
            else:
                self.add_error(
                    '"%s" version have unknown format. Should be either version string or dictionary with details' %
                    component)
                continue

        return self

    def validate_targets(self):
        targets = self.manifest_tree.get("targets", [])

        if isinstance(targets, str):
            targets = [targets]

        if not isinstance(targets, list):
            self.add_error("Unknown format for list of supported targets")
            return self

        unknown_targets = []
        for target in targets:
            if target not in self.KNOWN_PLATFORMS:
                unknown_targets.append(target)

        if unknown_targets:
            self.add_error("Unknown targets: %s" % ", ".join(unknown_targets))

        return self

    def validate_normalize(self):
        self.validate_root_keys().validate_root_values().validate_normalize_dependencies().validate_targets()
        return self._errors
