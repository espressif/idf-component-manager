# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import contextvars
import json
import os.path
import typing as t
from collections import defaultdict

if t.TYPE_CHECKING:
    from idf_component_tools.manifest import ComponentRequirement


class DebugInfoCollector:
    def __init__(self):
        self.msgs: t.List[str] = []
        self.dep_introduced_by: t.Dict[str, t.Set[str]] = defaultdict(set)

    def add_msg(self, message: str):
        self.msgs.append(message)

    def declare_dep(self, dep_name: str, introduced_by: str):
        self.dep_introduced_by[dep_name].add(introduced_by)


class SdkconfigContext:
    def __init__(self):
        self.sdkconfig: t.Dict[str, t.Any] = {}
        self.missed_keys: t.Dict[str, t.Set['ComponentRequirement']] = defaultdict(set)

    def update_from_file(self, file_path: str):
        if not os.path.isfile(file_path):
            return

        with open(file_path, encoding='utf8') as f:
            self.sdkconfig.update(json.load(f))

    def set_missed_kconfig(self, key: str, req: 'ComponentRequirement'):
        self.missed_keys[key].add(req)


DEBUG_INFO_COLLECTOR = contextvars.ContextVar('DebugInfoCollector', default=DebugInfoCollector())
KCONFIG_CONTEXT = contextvars.ContextVar('SdkconfigContext', default=SdkconfigContext())
