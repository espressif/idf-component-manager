import re

from semantic_version import Version

import idf_component_tools as tools

from .manifest import ComponentSpec

try:
    from typing import List, Set
except ImportError:
    pass

KNOWN_ROOT_KEYS = (
    'maintainers',
    'dependencies',
    'targets',
    'version',
    'description',
    'url',
)

KNOWN_TARGETS = (
    'esp32',
    'esp32s2',
)

REQUIRED_KEYS = ('version', )

SLUG_RE = re.compile(r'^[-a-z0-9_/]+\Z')


class ManifestValidator(object):
    """Validator for manifest object, checks for structure, known fields and valid values"""
    def __init__(self, parsed_manifest, check_required_fields=False):  # type: (dict, bool) -> None
        self.manifest_tree = parsed_manifest
        self._errors = []  # type: List[str]
        self.known_component_keys = set([])  # type: Set[str]
        for source in tools.sources.KNOWN_SOURCES:
            self.known_component_keys.update(source.known_keys())
        self.check_required_fields = check_required_fields

    @staticmethod
    def _validate_keys(manifest, known_keys):
        unknown_keys = []
        for key in manifest.keys():
            if key not in known_keys:
                unknown_keys.append(key)
        return unknown_keys

    def _validate_version_spec(self, component, spec):
        try:
            ComponentSpec(spec or '*')
        except ValueError:
            self.add_error('Version specifications for "%s" are invalid.' % component)

    def add_error(self, message):
        self._errors.append(message)

    def validate_root_keys(self):
        unknown = sorted(self._validate_keys(self.manifest_tree, KNOWN_ROOT_KEYS))
        if unknown:
            self.add_error('Unknown keys: %s' % ', '.join(unknown))

        return self

    def validate_root_values(self):
        version = self.manifest_tree.get('version', None)
        try:
            if version:
                Version.parse(version)
        except ValueError:
            self.add_error('Component version should be valid semantic version')

        return self

    def _check_name(self, component):
        if not SLUG_RE.match(component):
            self.add_error(
                'Component\'s name is not valid "%s", should contain only lowercase letters, numbers, /, _ and -.' %
                component)

        if '__' in component:
            self.add_error('Component\'s name "%s" should not contain two consecutive underscores.' % component)

    def validate_normalize_dependencies(self):
        if ('dependencies' not in self.manifest_tree.keys() or not self.manifest_tree['dependencies']):
            return self

        dependencies = self.manifest_tree['dependencies']

        # List of components should be a dictionary.
        if not isinstance(dependencies, dict):
            self.add_error(
                'List of dependencies should be a dictionary.'
                ' For example:\ndependencies:\n  some-component: ">=1.2.3,!=1.2.5"')

            return self

        for component, details in dependencies.items():
            self._check_name(component)

            if isinstance(details, str):
                dependencies[component] = details = {'version': details}

            if isinstance(details, dict):
                unknown = self._validate_keys(details, self.known_component_keys)
                if unknown:
                    self.add_error('Unknown attributes for component "%s": %s' % (component, ', '.join(unknown)))
                self._validate_version_spec(component, details.get('version', ''))
            else:
                self.add_error(
                    '"%s" version have unknown format. Should be either version string or dictionary with details' %
                    component)
                continue

        return self

    def validate_required_keys(self):
        '''Check for required keys in the manifest, if necessary'''
        if not self.check_required_fields:
            return self

        for key in REQUIRED_KEYS:
            if key not in self.manifest_tree:
                self.add_error('"%s" is required for this manifest' % key)

        return self

    def validate_targets(self):
        targets = self.manifest_tree.get('targets', [])

        if isinstance(targets, str):
            targets = [targets]

        if not isinstance(targets, list):
            self.add_error('Unknown format for list of supported targets')
            return self

        unknown_targets = []
        for target in targets:
            if target not in KNOWN_TARGETS:
                unknown_targets.append(target)

        if unknown_targets:
            self.add_error('Unknown targets: %s' % ', '.join(unknown_targets))

        return self

    def validate_normalize(self):
        self.validate_root_keys().validate_root_values().validate_normalize_dependencies().validate_targets(
        ).validate_required_keys()
        return self._errors
