# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import re
import typing as t
from pathlib import Path

from idf_component_tools import warn
from idf_component_tools.constants import DEFAULT_NAMESPACE
from idf_component_tools.manifest import WEB_DEPENDENCY_REGEX

from .helper import parse_constraint
from .mixology.range import Range
from .mixology.union import Union


def parse_constraint_line(
    line: str, line_no: t.Optional[int] = None
) -> t.Dict[str, t.Union[Union, Range]]:
    requirements: t.Dict[str, t.Union[Union, Range]] = {}

    line = line.strip().lower()
    if not line:
        return requirements

    base_err_msg = 'Invalid dependency format'
    base_err_msg += f' at line {line_no}:' if line_no is not None else ':'

    match = re.match(WEB_DEPENDENCY_REGEX, line)
    if not match:
        raise ValueError(
            f'{base_err_msg} "{line}". '
            f'Expected format: "namespace/component_name[VERSION_SPEC]" or "component_name[VERSION_SPEC]"'
        )

    name, spec = match.groups()
    if not spec:
        raise ValueError(
            f'{base_err_msg} "{line}". No version specification found. '
            f'Expected version constraint like ">=1.0.0" or "~=2.1.0"'
        )

    if '/' not in name:
        name = f'{DEFAULT_NAMESPACE}/{name}'

    constraint = parse_constraint(spec)
    requirements[name] = constraint

    return requirements


def parse_constraint_file(filepath: t.Union[str, Path]) -> t.Dict[str, t.Union[Union, Range]]:
    """Parse constraint file containing component constraints with required version specs.

    Supports formats:

    - namespace/component_name>=version
    - component_name>=version (for espressif components)
    - # comments (lines starting with # are skipped)
    - Lines with # after content have inline comments trimmed

    :param filepath: Path to constraint file
    :returns: Dictionary of component constraints
    """
    requirements: t.Dict[str, t.Union[Union, Range]] = {}

    if not os.path.isfile(filepath):
        warn(f'Constraint file {filepath} does not exist. Skipping parsing.')
        return requirements

    with open(filepath, encoding='utf-8') as fr:
        for line_num, line in enumerate(fr, 1):
            line = line.split('#')[0]
            requirements.update(parse_constraint_line(line, line_num))

    return requirements


def parse_constraint_string(s: str) -> t.Dict[str, t.Union[Union, Range]]:
    """Parse constraint string containing direct component constraints.

    Supports formats:

    - namespace/component_name>=version
    - component_name>=version (for espressif components)
    - Multiple constraints separated by semicolons
    - Does NOT support comments (unlike file parsing)

    :param s: String containing constraint definitions
    :returns: Dictionary of component constraints
    """
    requirements: t.Dict[str, t.Union[Union, Range]] = {}

    for line in s.split(';'):
        requirements.update(parse_constraint_line(line))

    return requirements
