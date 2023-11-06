# SPDX-FileCopyrightText: 2018-2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#
# Contains elements taken from "is-git-url" github repository
# https://github.com/jonschlinkert/is-git-url
# Copyright (c) 2017, Jon Schlinkert.
# Originally released under the MIT License.

import re
import sys

URL_RE = (
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+'
    r'(?:[A-Za-z]{2,6}\.?|[A-Za-z0-9-]{2,}\.?)|'  # domain
    r'localhost|'  # or localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$'
)
COMPILED_URL_RE = re.compile(URL_RE, re.IGNORECASE)

GIT_URL_RE = r'^(?:git|ssh|https?|git@[-\w.]+):(\/\/)?(.*)(\.git)?(/?|#[-\d\w._]+?)$'
COMPILED_GIT_URL_RE = re.compile(GIT_URL_RE, re.IGNORECASE)

FILE_RE = (
    r'^file://'  # file URI
    r'([A-Za-z]:\\\\(?:[^\\/:*?\"<>|\r\n]+\\)*$|'  # Windows path
    r'\/.*$)$'  # Unix path
)
COMPILED_FILE_RE = re.compile(FILE_RE, re.IGNORECASE)

# Registry related constants
DEFAULT_NAMESPACE = 'espressif'
IDF_COMPONENT_REGISTRY_URL = 'https://components.espressif.com/'
IDF_COMPONENT_STORAGE_URL = 'https://components-file.espressif.com/'

UPDATE_SUGGESTION = """
SUGGESTION: This component may be using a newer version of the component manager.
You can try to update the component manager by running:
    {} -m pip install --upgrade idf-component-manager
""".format(
    sys.executable
)
