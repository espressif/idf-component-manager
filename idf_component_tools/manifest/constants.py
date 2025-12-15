# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import re

SLUG_BODY_REGEX = r'[a-zA-Z\d]+(?:(?:[_-](?![_-]+))|(?:[a-zA-Z\d]))*[a-zA-Z\d]+'
SLUG_REGEX = r'^{}$'.format(SLUG_BODY_REGEX)
FULL_SLUG_REGEX = r'^((?:{slug}/{slug})|(?:{slug}))$'.format(slug=SLUG_BODY_REGEX)
COMPILED_FULL_SLUG_REGEX = re.compile(FULL_SLUG_REGEX)
WEB_DEPENDENCY_REGEX = r'^((?:{slug}/{slug})|(?:{slug}))(.*)$'.format(slug=SLUG_BODY_REGEX)
MAX_NAME_LENGTH = 64

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
