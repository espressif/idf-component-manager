# SPDX-FileCopyrightText: 2018-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#
# Contains elements taken from "is-git-url" github repository
# https://github.com/jonschlinkert/is-git-url
# Copyright (c) 2017, Jon Schlinkert.
# Originally released under the MIT License.

import re
import sys

GIT_URL_RE = r'^(?:git|ssh|https?|git@[-\w.]+):(\/\/)?(.*)(\.git)?(/?|#[-\d\w._]+?)$'
COMPILED_GIT_URL_RE = re.compile(GIT_URL_RE, re.IGNORECASE)
COMMIT_ID_RE = r'[0-9a-f]{40}'
COMPILED_COMMIT_ID_RE = re.compile(COMMIT_ID_RE)

# Registry related constants
DEFAULT_NAMESPACE = 'espressif'
IDF_COMPONENT_REGISTRY_URL = 'https://components.espressif.com/'
IDF_COMPONENT_STORAGE_URL = 'https://components-file.espressif.com/'
IDF_COMPONENT_STAGING_REGISTRY_URL = 'https://components-staging.espressif.com'

UPDATE_SUGGESTION = """
SUGGESTION: This component may be using a newer version of the component manager.
You can try to update the component manager by running:
    {} -m pip install --upgrade idf-component-manager
""".format(sys.executable)
MANIFEST_FILENAME = 'idf_component.yml'

KCONFIG_VAR_REGEX = re.compile(r'\$CONFIG\{([^}]+)}')
