# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import re

from schema import Schema, SchemaError

from idf_component_tools.utils import lru_cache

from ..errors import MetadataError, MetadataKeyError, SourceError
from ..messages import MetadataKeyWarning, MetadataWarning, hint
from .constants import FULL_SLUG_REGEX, known_targets
from .metadata import Metadata
from .schemas import BUILD_METADATA_KEYS, INFO_METADATA_KEYS, KNOWN_FILES_KEYS, schema_builder

try:
    from typing import List
except ImportError:
    pass


class ManifestValidator(object):
    SLUG_REGEX_COMPILED = re.compile(FULL_SLUG_REGEX)
    """Validator for manifest object, checks for structure, known fields and valid values"""

    def __init__(
        self,
        parsed_manifest,  # type: dict
        check_required_fields=False,  # type: bool
        metadata=None,  # type: Metadata | None
    ):  # type: (...) -> None
        self.manifest_tree = parsed_manifest
        self.metadata = metadata
        self._errors = []  # type: List[str]

        self.check_required_fields = check_required_fields

    @property
    @lru_cache(1)
    def schema(self):  # type: () -> Schema
        return schema_builder(validate_rules=False)

    def add_error(self, message):
        if message not in self._errors:
            self._errors.append(message)

    def validate_normalize_root_keys(self):  # type: () -> None
        if self.metadata is None:
            try:
                self.metadata = Metadata.load(manifest_tree=self.manifest_tree)
            except MetadataError as e:
                self._errors.extend(e.args)
                return

        for key in self.metadata.build_metadata_keys:
            if key not in BUILD_METADATA_KEYS:
                _k, _type = Metadata.get_closest_manifest_key_and_type(key)
                self.add_error(str(MetadataKeyError(_k, _type)))

        for key in self.metadata.info_metadata_keys:
            manifest_root_key = key.split('-')[0]

            # check if the info key is known
            if key not in INFO_METADATA_KEYS:
                _k, _type = Metadata.get_closest_manifest_key_and_type(key)
                hint(MetadataKeyWarning(_k, _type))
                if manifest_root_key in self.manifest_tree:
                    hint(
                        MetadataWarning(
                            'Dropping key "{}" from manifest.'.format(manifest_root_key)
                        )
                    )
                    self.manifest_tree.pop(manifest_root_key)

    def validate_normalize_dependencies(self):  # type: () -> None
        """Check dependencies section of the manifest"""

        # TODO: remove this import and avoid circular dependency somehow
        from idf_component_tools.sources import BaseSource

        def _check_name(name):  # type: (str) -> None
            if not self.SLUG_REGEX_COMPILED.match(name):
                self.add_error(
                    'Component\'s name is not valid "%s", should '
                    'contain only letters, numbers, /, _ and -.' % name
                )

            if '__' in name:
                self.add_error(
                    'Component\'s name "%s" should not contain two consecutive underscores.' % name
                )

        if (
            'dependencies' not in self.manifest_tree.keys()
            or not self.manifest_tree['dependencies']
        ):
            return

        dependencies = self.manifest_tree['dependencies']

        # List of components should be a dictionary.
        if not isinstance(dependencies, dict):
            self.add_error(
                'List of dependencies should be a dictionary.'
                ' For example:\ndependencies:\n  some-component: ">=1.2.3,!=1.2.5"'
            )

            return

        for component, details in dependencies.items():
            _check_name(component)

            if isinstance(details, str):
                dependencies[component] = details = {'version': details}

            if isinstance(details, dict):
                try:
                    sources = BaseSource.fromdict(component, details)  # type: ignore

                    for source in sources:
                        if not source.validate_version_spec(str(details.get('version', ''))):
                            self.add_error(
                                'Version specifications for "%s" are invalid.' % component
                            )

                        # check the version defined in optional requirements as well
                        optional_dependencies = details.get('rules', []) + details.get(
                            'matches', []
                        )
                        for rule in optional_dependencies:
                            if isinstance(rule, dict):
                                version = rule.get('version', '')
                            else:
                                version = rule.version or ''

                            if not source.validate_version_spec(version):
                                self.add_error(
                                    '"dependencies" version specifications for "%s" are invalid.'
                                    % component
                                )

                    if 'public' in details and 'require' in details:
                        self.add_error('Don\'t use "public" and "require" fields at the same time.')
                except SourceError as unknown_keys_error:
                    self.add_error(
                        str(unknown_keys_error).replace(
                            'dependency', 'dependency "{}"'.format(component)
                        )
                    )
            else:
                self.add_error(
                    '"%s" version have unknown format. Should be either version '
                    'string or dictionary with details' % component
                )
                continue

    def validate_normalize_required_keys(self):  # type: () -> None
        """Check for required keys in the manifest, if necessary"""
        if not self.check_required_fields:
            return

        if not self.manifest_tree.get('repository') and self.manifest_tree.get('commit_sha'):
            self.add_error(
                'The `repository` field is required in the `idf_component.yml` file when '
                'the `commit_sha` field is set. Please make sure to include the '
                'repository URL or delete the `commit_sha` field'
            )

        if not self.manifest_tree.get('version'):
            self.add_error(
                '"version" field is required in the "idf_component.yml" '
                'manifest when uploading to the registry.'
            )

    def validate_targets(self):  # type: () -> None
        targets = self.manifest_tree.get('targets', [])

        if isinstance(targets, str):
            targets = [targets]

        if not isinstance(targets, list):
            self.add_error(
                'Unknown format for list of supported targets. '
                'It should be a list of targets, like [esp32, esp32s2]'
            )
            return

        # Check fields only during uploads to the registry
        if not self.check_required_fields:
            return

        unknown_targets = []
        for target in targets:
            if target not in known_targets():
                unknown_targets.append(target)

        if unknown_targets:
            self.add_error('Unknown targets: %s' % ', '.join(unknown_targets))

    def validate_files(self):  # type: () -> None
        """Check include/exclude patterns"""
        files = self.manifest_tree.get('files', {})
        for key in files:
            if key not in KNOWN_FILES_KEYS:
                self.add_error('"files" section contains unknown key: %s' % key)

    def validate_normalize_schema(self):
        try:
            self.manifest_tree = self.schema.validate(self.manifest_tree)
        except SchemaError as e:
            # Some format errors may not have detailed description, so avoid duplications
            errors = list(filter(None, e.errors))
            self._errors.extend(sorted(set(errors), key=errors.index))

    def validate_duplicates(self, tree):
        for k, v in tree.items():
            if isinstance(v, list):
                v = [i.lower() for i in v if isinstance(i, str)]
                duplicates = set([i for i in v if v.count(i) > 1])
                if duplicates:
                    self.add_error('Duplicate item in "{}": {}'.format(k, duplicates))

            if isinstance(v, dict):
                self.validate_duplicates(v)

    def validate_normalize(self):  # type: () -> list[str]
        self.validate_normalize_root_keys()
        self.validate_normalize_schema()
        self.validate_normalize_dependencies()
        self.validate_targets()
        self.validate_normalize_required_keys()
        self.validate_files()
        self.validate_duplicates(self.manifest_tree)
        return self._errors


class ExpandedManifestValidator(ManifestValidator):
    """Manifest Validator for the case of expanded environment variables"""

    @property
    @lru_cache(1)
    def schema(self):  # type: () -> Schema
        return schema_builder(validate_rules=True)
