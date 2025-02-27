# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import re
import sys
import typing as t

from idf_component_tools import ComponentManagerSettings

SLUG_BODY_REGEX = r'[a-zA-Z\d]+(?:(?:[_-](?![_-]+))|(?:[a-zA-Z\d]))*[a-zA-Z\d]+'
SLUG_REGEX = r'^{}$'.format(SLUG_BODY_REGEX)
FULL_SLUG_REGEX = r'^((?:{slug}/{slug})|(?:{slug}))$'.format(slug=SLUG_BODY_REGEX)
COMPILED_FULL_SLUG_REGEX = re.compile(FULL_SLUG_REGEX)
WEB_DEPENDENCY_REGEX = r'^((?:{slug}/{slug})|(?:{slug}))(.*)$'.format(slug=SLUG_BODY_REGEX)

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
    'esp32c61',
    'esp32h2',
    'esp32h21',
    'esp32h4',
    'esp32p4',
    'linux',
]


def known_targets() -> t.List[str]:
    env_targets = ComponentManagerSettings().KNOWN_TARGETS
    if env_targets:
        try:
            targets = env_targets.split(',')
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
