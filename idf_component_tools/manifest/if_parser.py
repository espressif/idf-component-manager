# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import re
from ast import literal_eval

from schema import SchemaError

from idf_component_tools.build_system_tools import get_env_idf_target, get_idf_version
from idf_component_tools.errors import FetchingError, ProcessingError
from idf_component_tools.manifest.constants import IF_IDF_VERSION_REGEX, IF_TARGET_REGEX
from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.serialization import serializable

try:
    from typing import Literal
except ImportError:
    pass

IF_IDF_VERSION_REGEX_COMPILED = re.compile(IF_IDF_VERSION_REGEX)
IF_TARGET_REGEX_COMPILED = re.compile(IF_TARGET_REGEX)


@serializable
class IfClause:
    _serialization_properties = [
        'clause',
        'bool_value',
    ]

    @staticmethod
    def eval_str(s):  # type: (str) -> str
        _s = s.strip()
        if not (_s[0] == _s[-1] == '"'):
            _s = '"{}"'.format(_s.replace('"', r'\"'))

        try:
            return literal_eval(_s)
        except (ValueError, SyntaxError):
            raise SchemaError(None, 'Invalid string "{}" in "if" clause'.format(s))

    @staticmethod
    def eval_list(s):  # type: (str) -> list[str]
        _s = s.strip()

        if _s[0] == '[' and _s[-1] == ']':
            _s = _s[1:-1]

        try:
            return [IfClause.eval_str(part) for part in _s.split(',')]
        except (ValueError, SyntaxError):
            raise SchemaError(None, 'Invalid list "{}" in "if" clause'.format(s))

    @staticmethod
    def regex_str():
        if_idf_version = IF_IDF_VERSION_REGEX
        # remove the name group
        if_idf_version = re.sub(r'\(\?P<\w+>', '(?:', if_idf_version)
        # remove the first ^ and the last $ and make it as a group
        if_idf_version = '(' + if_idf_version[1:-1] + ')'

        if_target = IF_TARGET_REGEX
        # remove the name group
        if_target = re.sub(r'\(\?P<\w+>', '(?:', if_target)
        # remove the first ^ and the last $ and make it as a group
        if_target = '(' + if_target[1:-1] + ')'

        return '^{}|{}$'.format(if_idf_version, if_target)

    @classmethod
    def from_string(cls, s):  # type: (str) -> IfClause
        return parse_if_clause(s)


class IfIdfVersionClause(IfClause):
    def __init__(self, spec):  # type: (str) -> None
        self.spec = spec

    def __repr__(self):  # type: () -> str
        return '{} ({})'.format(self.clause, self.bool_value)

    @property
    def clause(self):  # type: () -> str
        return 'idf_version {}'.format(self.spec)

    @property
    def bool_value(self):  # type: () -> bool
        try:
            idf_version = get_idf_version()
        except FetchingError:
            return False

        return SimpleSpec(self.spec).match(Version(idf_version))


@serializable
class IfTargetClause(IfClause):
    def __init__(self, operator, target_str):  # type: (Literal['==', '!=', 'in', 'not in'], str) -> None
        self.operator = operator
        self.target_str = target_str

    def __repr__(self):
        return '{} ({})'.format(self.clause, self.bool_value)

    @property
    def clause(self):  # type: () -> str
        return 'target {} {}'.format(self.operator, self.target_str)

    @property
    def bool_value(self):
        try:
            env_target = get_env_idf_target()
        except ProcessingError:
            return False

        if self.operator == '!=':
            return env_target != self.eval_str(self.target_str)

        if self.operator == '==':
            return env_target == self.eval_str(self.target_str)

        if self.operator == 'not in':
            return env_target not in self.eval_list(self.target_str)

        if self.operator == 'in':
            return env_target in self.eval_list(self.target_str)


def _parse_if_idf_version_clause(mat):  # type: (re.Match) -> IfClause
    comparison = mat.group('comparison')
    spec = mat.group('spec')
    spec = ','.join([part.strip() for part in spec.split(',')])

    try:
        simple_spec = SimpleSpec('{}{}'.format(IfClause.eval_str(comparison), IfClause.eval_str(spec)))
    except ValueError:
        raise SchemaError(
            None,
            'Invalid version specification for "idf_version": {clause}. Please use a format like '
            '"idf_version >=4.4,<5.3"\nDocumentation: '
            'https://docs.espressif.com/projects/idf-component-manager/en/latest/reference/manifest_file.html#rules'.
            format(clause=mat.string),
        )

    return IfIdfVersionClause(str(simple_spec))


def _parser_if_target_clause(mat):  # type: (re.Match) -> IfClause
    operator = mat.group('comparison')
    target_str = mat.group('targets').strip()

    if operator not in ['==', '!=', 'in', 'not in']:
        raise SchemaError(
            None,
            'Invalid if clause format for target: {clause}. You can specify rules based on target using '
            '"==", "!=", "in" or "not in" like: "target in [esp32, esp32c3]", "target == esp32"\n'
            'Documentation: '
            'https://docs.espressif.com/projects/idf-component-manager/en/latest/reference'
            '/manifest_file.html#rules'.format(clause=mat.string),
        )

    return IfTargetClause(operator, target_str)


def parse_if_clause(if_clause):  # type: (str) -> IfClause
    res = IF_IDF_VERSION_REGEX_COMPILED.match(if_clause)
    if res:
        return _parse_if_idf_version_clause(res)

    res = IF_TARGET_REGEX_COMPILED.match(if_clause)
    if res:
        return _parser_if_target_clause(res)

    raise SchemaError(
        None,
        'Invalid if clause format "{clause}". You can specify rules based on current ESP-IDF version or target like: '
        '"idf_version >=3.3,<5.0" or "target in [esp32, esp32c3]"\nDocumentation: '
        'https://docs.espressif.com/projects/idf-component-manager/en/latest/reference/manifest_file.html#rules'.format(
            clause=if_clause),
    )
