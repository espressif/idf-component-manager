# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


import typing as t

from pydantic import ValidationError
from ruamel.yaml import YAML, YAMLError

from idf_component_tools.errors import ProcessingError
from idf_component_tools.utils import BaseModel, TypedDict


class LocalComponent(TypedDict):
    name: str
    path: str


class LocalComponentList(BaseModel):
    components: t.List[LocalComponent]


def parse_component_list(path: str) -> t.List[t.Dict[str, str]]:
    with open(path, encoding='utf-8') as f:
        try:
            components = LocalComponentList.fromdict(YAML(typ='safe').load(f))
            return [c for c in components.components]  # type: ignore
        except (YAMLError, ValidationError):
            raise ProcessingError('Cannot parse components list file.')
