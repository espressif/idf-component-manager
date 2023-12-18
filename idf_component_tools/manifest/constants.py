# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import sys

MANIFEST_FILENAME = 'idf_component.yml'
SLUG_BODY_REGEX = r'[a-zA-Z\d]+(?:(?:[_-](?![_-]+))|(?:[a-zA-Z\d]))*[a-zA-Z\d]+'
SLUG_REGEX = r'^{}$'.format(SLUG_BODY_REGEX)
FULL_SLUG_REGEX = r'^((?:{slug}/{slug})|(?:{slug}))$'.format(slug=SLUG_BODY_REGEX)
TAGS_REGEX = r'^[A-Za-z0-9\_\-]{3,32}$'
WEB_DEPENDENCY_REGEX = r'^((?:{slug}/{slug})|(?:{slug}))(.*)$'.format(slug=SLUG_BODY_REGEX)
COMMIT_ID_RE = r'[0-9a-f]{40}'
IF_IDF_VERSION_REGEX = r'^(?P<keyword>idf_version) *(?P<comparison>[\^=~<>!]+)(?P<spec>.+)$'
IF_TARGET_REGEX = r'^(?P<keyword>target) *(?P<comparison>!=|==|not in|in)(?P<targets>.+)$'

LINKS = ['repository', 'documentation', 'issues', 'discussion', 'url']
KNOWN_INFO_METADATA_FIELDS = [
    'maintainers',
    'description',
    'tags',
    'examples',
    'license',
    'repository_info',
] + LINKS
KNOWN_BUILD_METADATA_FIELDS = ['name', 'dependencies', 'targets', 'version', 'files']

DEFAULT_KNOWN_TARGETS = [
    'esp32',
    'esp32s2',
    'esp32c3',
    'esp32s3',
    'esp32c2',
    'esp32c5',
    'esp32c6',
    'esp32h2',
    'esp32p4',
    'linux',
]


def known_targets():  # type: () -> list[str]
    try:
        targets = os.environ['IDF_COMPONENT_MANAGER_KNOWN_TARGETS'].split(',')
        if any(targets):
            return targets
    except KeyError:
        pass

    try:
        idf_path = os.environ['IDF_PATH']
    except KeyError:
        return DEFAULT_KNOWN_TARGETS

    try:
        sys.path.append(os.path.join(idf_path, 'tools'))
        from idf_py_actions.constants import PREVIEW_TARGETS, SUPPORTED_TARGETS

        return SUPPORTED_TARGETS + PREVIEW_TARGETS
    except ImportError:
        return DEFAULT_KNOWN_TARGETS
