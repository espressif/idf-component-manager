# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from typing import List, Type

from .base import BaseSource
from .git import GitSource
from .idf import IDFSource
from .local import LocalSource
from .web_service import WebServiceSource

KNOWN_SOURCES = [
    IDFSource,
    GitSource,
    LocalSource,
    WebServiceSource,
]  # type: List[Type[BaseSource]]

__all__ = [
    'BaseSource',
    'WebServiceSource',
    'LocalSource',
    'IDFSource',
    'GitSource',
    'KNOWN_SOURCES',
]
