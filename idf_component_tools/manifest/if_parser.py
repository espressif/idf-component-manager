# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import typing as t
from ast import literal_eval

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from pyparsing import (
    Keyword,
    Literal,
    MatchFirst,
    ParseResults,
    Regex,
    Word,
    alphas,
    infixNotation,
    nums,
    opAssoc,
)

from idf_component_tools.build_system_tools import get_env_idf_target, get_idf_version
from idf_component_tools.errors import RunningEnvironmentError
from idf_component_tools.messages import warn
from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.utils import subst_vars_in_str


class Stmt:
    def __repr__(self):
        return self.stmt

    @staticmethod
    def eval_str(s: str) -> str:
        _s = s.strip()
        if not (_s[0] == _s[-1] == '"'):
            _s = '"{}"'.format(_s.replace('"', r'\"'))

        try:
            return literal_eval(_s)
        except (ValueError, SyntaxError):
            raise ValueError('Invalid string "{}" in "if" clause'.format(s))

    @staticmethod
    def eval_list(s: str) -> t.List[str]:
        _s = s.strip()

        if _s[0] == '[' and _s[-1] == ']':
            _s = _s[1:-1]

        try:
            return [Stmt.eval_str(part) for part in _s.split(',')]
        except (ValueError, SyntaxError):
            raise ValueError('Invalid list "{}" in "if" clause'.format(s))

    def get_value(self) -> t.Any:
        raise NotImplementedError('Please implement this function in sub classes')


class LeftValue(Stmt):
    def __init__(self, stmt: str) -> None:
        self.stmt = stmt

    def get_value(self) -> str:
        if self.stmt == 'idf_version':
            try:
                return get_idf_version()
            except RunningEnvironmentError:
                warn('Running in an environment without IDF. Using "0.0.0" as the IDF version')
                return '0.0.0'

        if self.stmt == 'target':
            try:
                return get_env_idf_target()
            except RunningEnvironmentError:
                warn('Running in an environment without IDF. Using "unknown" as IDF target')
                return 'unknown'

        return subst_vars_in_str(self.stmt)


class String(Stmt):
    def __init__(self, stmt: str) -> None:
        self.stmt = stmt

    def get_value(self) -> str:
        return self.eval_str(self.stmt)


class List(Stmt):
    def __init__(self, stmt: str) -> None:
        self.stmt = stmt

    def get_value(self) -> t.List[str]:
        return self.eval_list(self.stmt)


class IfClause(Stmt):
    # WARNING: sequence of operators is important
    # For example, `not in` should be checked before `in` because `in` is a substring of `not in`

    # used with both version specs and list of strings
    REUSED_OP_LIST = [
        '!=',
        '==',
    ]

    # only used with version specs
    VERSION_OP_LIST = [
        '<=',
        '<',
        '>=',
        '>',
        '~=',
        '~',
        '=',
        '^',
    ]

    # only used with list of strings
    LIST_OP_LIST = [
        'not in',
        'in',
    ]

    def __init__(self, left: LeftValue, op: str, right: t.Union[String, List]):
        self.left: LeftValue = left
        self.op: t.Optional[str] = op
        self.right: t.Union[String, List] = right

    @property
    def stmt(self):
        return '{} {} {}'.format(self.left, self.op, self.right)

    def _get_value_as_version(self, _l: str, _r: t.Union[str, t.List[str]]) -> bool:
        if isinstance(_r, list):
            raise ValueError(
                f'Operator {self.op} only supports string on the right side. Got "{_r}"'
            )

        def _clear_spaces(*s: str) -> str:
            return ''.join(s).replace(' ', '')

        spec_without_spaces = _clear_spaces(self.op or '', _r)
        try:
            spec = SimpleSpec(spec_without_spaces)
        except ValueError:
            raise ValueError(f'Invalid version spec "{spec_without_spaces}"')

        try:
            version = Version.coerce(_l)
        except ValueError:
            raise ValueError(f'Invalid version spec "{_l}"')

        return spec.match(version)

    def _get_value_as_string(self, _l: str, _r: t.Union[str, t.List[str]]) -> bool:
        if isinstance(_r, list):
            raise ValueError(
                f'Operator {self.op} only supports string on the right side. Got "{_r}"'
            )

        if self.op == '==':
            return _l == _r

        if self.op == '!=':
            return _l != _r

        raise ValueError(f'Support operators: "==,!=". Got "{self.op}"')

    def _get_value_as_list(self, _l: str, _r: t.Union[str, t.List[str]]) -> bool:
        if isinstance(_r, str):
            raise ValueError(
                f'Operator {self.op} only supports list of strings on the right side. Got "{_r}"'
            )

        if self.op == 'in':
            return _l in _r

        if self.op == 'not in':
            return _l not in _r

        raise ValueError(f'Support operators: "in,not in". Got "{self.op}"')

    def get_value(self) -> bool:
        return self._get_value()

    def _get_value(self) -> bool:
        _l = self.left.get_value()
        _r = self.right.get_value()

        if self.op in self.LIST_OP_LIST:
            return self._get_value_as_list(_l, _r)
        elif self.op in self.VERSION_OP_LIST:
            return self._get_value_as_version(_l, _r)
        elif self.op in self.REUSED_OP_LIST and isinstance(_r, str):
            # if the right value could be a version spec, compare it as a version spec
            # otherwise, compare it as a string
            try:
                SimpleSpec(self.op + _r)
            except ValueError:
                return self._get_value_as_string(_l, _r)
            else:
                return self._get_value_as_version(_l, _r)
        elif self.op in self.REUSED_OP_LIST and isinstance(_r, list):
            raise ValueError(
                f'Operator {self.op} only supports string on the right side. Got "{_r}"'
            )

        raise ValueError(
            f'Support operators: "{",".join(self.LIST_OP_LIST + self.VERSION_OP_LIST + self.REUSED_OP_LIST)}". Got "{self.op}"'
        )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: t.Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema(min_length=1)


class BoolAnd(Stmt):
    def __init__(self, x: ParseResults):
        self.left: IfClause = x[0][0]
        self.right: IfClause = x[0][2]

    @property
    def stmt(self) -> str:
        return '{} and {}'.format(self.left, self.right)

    def get_value(self) -> bool:
        return self.left.get_value() and self.right.get_value()


class BoolOr(Stmt):
    def __init__(self, x: ParseResults):
        self.left: IfClause = x[0][0]
        self.right: IfClause = x[0][2]

    @property
    def stmt(self):  # type: () -> str
        return '{} or {}'.format(self.left, self.right)

    def get_value(self) -> bool:
        return self.left.get_value() or self.right.get_value()


_non_terminator_words = Regex(r'[^\n\r\[\]&|\(\)]+')
LEFT_VALUE = Word(alphas + nums + '${}_-').setParseAction(lambda x: LeftValue(x[0]))

OPERATORS = MatchFirst(
    Literal(op)
    for op in [
        *IfClause.REUSED_OP_LIST,
        *IfClause.VERSION_OP_LIST,
        *IfClause.LIST_OP_LIST,
    ]
).setParseAction(lambda x: x[0])

STRING = _non_terminator_words.setParseAction(lambda x: String(x[0]))
LIST = (Literal('[') + STRING + Literal(']')).setParseAction(lambda x: List(f'{x[0]}{x[1]}{x[2]}'))

IF_CLAUSE = (LEFT_VALUE + OPERATORS + (LIST | STRING)).setParseAction(
    lambda x: IfClause(x[0], x[1], x[2])
)


AND = Keyword('&&')
OR = Keyword('||')

BOOL_EXPR = infixNotation(
    IF_CLAUSE,
    [
        (AND, 2, opAssoc.LEFT, BoolAnd),
        (OR, 2, opAssoc.LEFT, BoolOr),
    ],
)


def parse_if_clause(s):  # type: (str) -> IfClause
    return BOOL_EXPR.parseString(s, parseAll=True)[0]
