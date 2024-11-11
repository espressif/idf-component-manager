# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import contextvars
import typing as t
from collections import defaultdict


class DebugInfoCollector:
    def __init__(self):
        self.msgs: t.List[str] = []
        self.dep_introduced_by: t.Dict[str, t.Set[str]] = defaultdict(set)

    def add_msg(self, message: str):
        self.msgs.append(message)

    def declare_dep(self, dep_name: str, introduced_by: str):
        self.dep_introduced_by[dep_name].add(introduced_by)


DEBUG_INFO_COLLECTOR = contextvars.ContextVar('DebugInfoCollector', default=DebugInfoCollector())
