# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import typing as t

from .base import BaseSource
from .git import GitSource
from .idf import IDFSource
from .local import LocalSource
from .web_service import WebServiceSource

KNOWN_SOURCES: t.List[t.Type[BaseSource]] = [
    IDFSource,
    GitSource,
    LocalSource,
    WebServiceSource,
]

__all__ = [
    'BaseSource',
    'WebServiceSource',
    'LocalSource',
    'IDFSource',
    'GitSource',
    'KNOWN_SOURCES',
]
