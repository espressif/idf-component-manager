# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re
import typing as t
from ast import literal_eval

from pyparsing import Keyword, Word, alphanums, infixNotation, opAssoc
from schema import SchemaError

from idf_component_tools.build_system_tools import get_env_idf_target, get_idf_version
from idf_component_tools.errors import FetchingError, ProcessingError
from idf_component_tools.manifest.constants import IF_IDF_VERSION_REGEX, IF_TARGET_REGEX
from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.serialization import serializable

IF_IDF_VERSION_REGEX_COMPILED = re.compile(IF_IDF_VERSION_REGEX)
IF_TARGET_REGEX_COMPILED = re.compile(IF_TARGET_REGEX)


@serializable
class OptionalDependency:
    _serialization_properties = [
        'if_clause',
        'version',
    ]

    def __init__(self, clause: t.Union[str, IfClause], version: t.Optional[str] = None) -> None:
        if isinstance(clause, IfClause):
            self.if_clause = clause
        else:
            self.if_clause = IfClause.from_string(clause)
        self.version = version

    def __repr__(self) -> str:
        return '{} ({})'.format(self.if_clause, self.version or '*')

    @classmethod
    def fromdict(cls, d: t.Dict) -> OptionalDependency:
        return cls(d.get('if'), d.get('version'))  # type: ignore


@serializable
class IfClause:
    _serialization_properties = [
        'clause',
        'bool_value',
    ]

    @staticmethod
    def eval_str(s: str) -> str:
        _s = s.strip()
        if not (_s[0] == _s[-1] == '"'):
            _s = '"{}"'.format(_s.replace('"', r'\"'))

        try:
            return literal_eval(_s)
        except (ValueError, SyntaxError):
            raise SchemaError(None, f'Invalid string "{s}" in "if" clause')

    @staticmethod
    def eval_list(s: str) -> t.List[str]:
        _s = s.strip()

        if _s[0] == '[' and _s[-1] == ']':
            _s = _s[1:-1]

        try:
            return [IfClause.eval_str(part) for part in _s.split(',')]
        except (ValueError, SyntaxError):
            raise SchemaError(None, f'Invalid list "{s}" in "if" clause')

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

        return f'^{if_idf_version}|{if_target}$'

    @classmethod
    def from_string(cls, s: str) -> IfClause:
        return parse_if_clause(s)

    @property
    def clause(self) -> str:
        raise NotImplementedError

    @property
    def bool_value(self) -> bool:
        raise NotImplementedError


class IfIdfVersionClause(IfClause):
    def __init__(self, spec: str) -> None:
        self.spec = spec

    def __repr__(self) -> str:
        return f'{self.clause} ({self.bool_value})'

    @property
    def clause(self) -> str:
        return f'idf_version {self.spec}'

    @property
    def bool_value(self) -> bool:
        try:
            idf_version = get_idf_version()
        except FetchingError:
            return False

        return SimpleSpec(self.spec).match(Version(idf_version))


@serializable
class IfTargetClause(IfClause):
    def __init__(self, operator: str, target_str: str):
        """
        Initialize the IfParser object.

        :param operator: The operator to be used for comparison. One of '==', '!=', 'in', 'not in'.
        :type operator: str
        :param target_str: The target string to be compared.
        :type target_str: str
        :returns: None
        """
        self.operator = operator
        self.target_str = target_str

    def __repr__(self):
        return f'{self.clause} ({self.bool_value})'

    @property
    def clause(self) -> str:
        return f'target {self.operator} {self.target_str}'

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


class BoolAnd(IfClause):
    def __init__(self, t):
        self.left: IfClause = t[0][0]
        self.right: IfClause = t[0][2]

    @property
    def clause(self) -> str:
        return f'{self.left.clause} and {self.right.clause}'

    @property
    def bool_value(self) -> bool:
        return self.left.bool_value and self.right.bool_value


class BoolOr(IfClause):
    def __init__(self, t):
        self.left: IfClause = t[0][0]
        self.right: IfClause = t[0][2]

    @property
    def clause(self) -> str:
        return f'{self.left.clause} or {self.right.clause}'

    @property
    def bool_value(self) -> bool:
        return self.left.bool_value or self.right.bool_value


def _parse_if_idf_version_clause(mat: re.Match) -> IfClause:
    comparison = mat.group('comparison')
    spec = mat.group('spec')
    spec = ','.join([part.strip() for part in spec.split(',')])

    try:
        simple_spec = SimpleSpec(f'{IfClause.eval_str(comparison)}{IfClause.eval_str(spec)}')
    except ValueError:
        raise SchemaError(
            None,
            'Invalid version specification for "idf_version": {clause}. Please use a format like '
            '"idf_version >=4.4,<5.3"\nDocumentation: '
            'https://docs.espressif.com/projects/idf-component-manager/'
            'en/latest/reference/manifest_file.html#rules'.format(clause=mat.string),
        )

    return IfIdfVersionClause(str(simple_spec))


def _parser_if_target_clause(mat: re.Match) -> IfClause:
    operator = mat.group('comparison')
    target_str = mat.group('targets').strip()

    if operator not in ['==', '!=', 'in', 'not in']:
        raise SchemaError(
            None,
            'Invalid if clause format for target: {clause}. '
            'You can specify rules based on target using '
            '"==", "!=", "in" or "not in" like: "target in [esp32, esp32c3]", "target == esp32"\n'
            'Documentation: '
            'https://docs.espressif.com/projects/idf-component-manager/en/latest/reference'
            '/manifest_file.html#rules'.format(clause=mat.string),
        )

    return IfTargetClause(operator, target_str)


def _parse_if_clause(s: str) -> IfClause:
    s = s.strip()
    res = IF_IDF_VERSION_REGEX_COMPILED.match(s)
    if res:
        return _parse_if_idf_version_clause(res)

    res = IF_TARGET_REGEX_COMPILED.match(s)
    if res:
        return _parser_if_target_clause(res)

    raise SchemaError(
        None,
        'Invalid if clause format "{clause}". '
        'You can specify rules based on current ESP-IDF version or target like: '
        '"idf_version >=3.3,<5.0" or "target in [esp32, esp32c3]"\nDocumentation: '
        'https://docs.espressif.com/projects/idf-component-manager/en/latest/reference/manifest_file.html#rules'.format(  # noqa
            clause=s
        ),
    )


AND = Keyword('&&')
OR = Keyword('||')

CLAUSE = Word(alphanums + ' _.^=~<>![,]"').setParseAction(lambda t: _parse_if_clause(t[0]))

BOOL_EXPR = infixNotation(
    CLAUSE,
    [
        (AND, 2, opAssoc.LEFT, BoolAnd),
        (OR, 2, opAssoc.LEFT, BoolOr),
    ],
)


def parse_if_clause(s: str) -> IfClause:
    return BOOL_EXPR.parseString(s, parseAll=True)[0]
