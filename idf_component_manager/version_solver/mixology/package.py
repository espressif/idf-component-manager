# SPDX-FileCopyrightText: 2018 Sébastien Eustace
# SPDX-License-Identifier: MIT License
# SPDX-FileContributor: 2022-2024 Espressif Systems (Shanghai) CO LTD
from __future__ import annotations

import typing as t

from idf_component_tools.sources import BaseSource


class Package:
    """
    A project's package.
    """

    ROOT_PACKAGE_NAME = '_root_'

    def __init__(self, name: str, source: t.Optional[BaseSource] = None) -> None:
        self._name = name
        self._source = source

    @classmethod
    def root(cls) -> Package:
        return Package(cls.ROOT_PACKAGE_NAME)

    @property
    def name(self) -> str:
        return self._name

    @property
    def source(self) -> BaseSource:
        return self._source

    def __eq__(self, other: Package) -> bool:
        if not isinstance(other, Package):
            return NotImplemented

        return self.name == other.name and self.source == other.source

    def __ne__(self, other: Package) -> bool:
        if not isinstance(other, Package):
            return NotImplemented

        return not (self == other)

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f'Package("{self.name}" {self.source})'

    def __hash__(self):
        return hash(self.name)
