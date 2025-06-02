# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
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
from idf_component_tools.constants import KCONFIG_VAR_REGEX
from idf_component_tools.debugger import KCONFIG_CONTEXT
from idf_component_tools.errors import MissingKconfigError, RunningEnvironmentError
from idf_component_tools.messages import warn
from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.utils import subst_vars_in_str

_value_type = t.Union[str, int, bool, Version]


class Stmt:
    def __repr__(self):
        return self.stmt

    @staticmethod
    def eval_bool(s: str) -> bool:
        _s = s.strip()
        if _s == 'True':
            return True

        if _s == 'False':
            return False

        raise ValueError('Invalid boolean "{}" in "if" clause'.format(s))

    @staticmethod
    def eval_int(s: str) -> int:
        _s = s.strip()
        try:
            return int(_s, 16) if _s.startswith('0x') else int(_s)
        except ValueError:
            raise ValueError('Invalid integer "{}" in "if" clause'.format(s))

    @staticmethod
    def eval_version(s: str) -> Version:
        _s = s.strip()
        try:
            return Version(_s)
        except ValueError:
            raise ValueError('Invalid version "{}" in "if" clause'.format(s))

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
    def eval_single(s: str) -> _value_type:
        # bool > int > version > str
        try:
            return Stmt.eval_bool(s)
        except ValueError:
            pass

        try:
            return Stmt.eval_int(s)
        except ValueError:
            pass

        try:
            return Stmt.eval_version(s)
        except ValueError:
            pass

        return Stmt.eval_str(s)

    @staticmethod
    def eval_list(s: str) -> t.List[_value_type]:
        _s = s.strip()

        if _s[0] == '[' and _s[-1] == ']':
            _s = _s[1:-1]

        try:
            return [Stmt.eval_single(part) for part in _s.split(',')]
        except (ValueError, SyntaxError):
            raise ValueError('Invalid list "{}" in "if" clause'.format(s))

    def get_value(self) -> t.Any:
        raise NotImplementedError('Please implement this function in sub classes')


class LeftValue(Stmt):
    def __init__(self, stmt: str) -> None:
        self.stmt = stmt

    def get_value(self) -> _value_type:
        _s = self.stmt.strip()
        if _s == 'idf_version':
            try:
                return Version(get_idf_version())
            except RunningEnvironmentError:
                warn('Running in an environment without IDF. Using "0.0.0" as the IDF version')
                return Version('0.0.0')

        if _s == 'target':
            try:
                return get_env_idf_target()
            except RunningEnvironmentError:
                warn('Running in an environment without IDF. Using "unknown" as IDF target')
                return 'unknown'

        # consider it as a kconfig
        match_s = KCONFIG_VAR_REGEX.match(_s)
        if match_s:
            key = match_s.group(1)
            kconfig_ctx = KCONFIG_CONTEXT.get()
            if key in kconfig_ctx.sdkconfig:
                return kconfig_ctx.sdkconfig[key]
            else:
                raise MissingKconfigError(key)

        return self.eval_single(subst_vars_in_str(_s))


class Single(Stmt):
    def __init__(self, stmt: str) -> None:
        self.stmt = stmt

    def get_value(self) -> _value_type:
        return self.eval_single(subst_vars_in_str(self.stmt))


class List(Stmt):
    def __init__(self, stmt: str) -> None:
        self.stmt = stmt

    def get_value(self) -> t.List[_value_type]:
        return self.eval_list(self.stmt)


class IfClause(Stmt):
    _OP_LAMBDA_MAP = {
        '<=': lambda x, y: x <= y,
        '<': lambda x, y: x < y,
        '>=': lambda x, y: x >= y,
        '>': lambda x, y: x > y,
        '==': lambda x, y: x == y,
        '!=': lambda x, y: x != y,
        'not in': lambda x, y: x not in y,
        'in': lambda x, y: x in y,
    }

    _LIST_OPS = ['not in', 'in']

    def __init__(self, left: LeftValue, op: str, right: t.Union[Single, List]):
        self.left: LeftValue = left
        self.op = op
        self.right: t.Union[Single, List] = right

    @property
    def stmt(self):
        return '{} {} {}'.format(self.left, self.op, self.right)

    @staticmethod
    def eval_spec(op: str, right: str) -> SimpleSpec:
        spec_without_spaces = f'{op}{right}'.replace(' ', '')
        try:
            spec = SimpleSpec(spec_without_spaces)
        except ValueError:
            raise ValueError(f'Invalid version spec "{spec_without_spaces}"')

        return spec

    def get_value(self) -> bool:  # type: ignore
        def raise_invalid_type_error() -> None:
            raise ValueError(
                f'Invalid operator "{self.op}" for comparing "{self.left}" and "{self.right}". \n'
                f'Please check documentation https://docs.espressif.com/projects/idf-component-manager/en/latest/reference/manifest_file.html#conditional-dependencies'
            )

        _l = self.left.get_value()
        _r_stmt = subst_vars_in_str(self.right.stmt)

        # idf_version compare with version spec
        if isinstance(_l, Version):
            if _r_stmt[0] == _r_stmt[-1] == '"':
                # this is to keep the backward compatibility
                _r_stmt = _r_stmt[1:-1]
            _spec = self.eval_spec(self.op, _r_stmt)
            return _spec.match(_l)

        # target only support !=, ==, in, not in
        if self.left.stmt.strip() == 'target':
            if self.op in ['==', '!=']:
                return self._OP_LAMBDA_MAP[self.op](_l, self.eval_str(self.right.stmt))
            elif self.op in self._LIST_OPS:
                return self._OP_LAMBDA_MAP[self.op](_l, self.eval_list(self.right.stmt))
            else:
                raise_invalid_type_error()

        # env var, kconfig, string, compare with string, int, bool, as the left value
        try:
            if self.op in self._LIST_OPS:
                return self._OP_LAMBDA_MAP[self.op](str(_l), self.eval_list(_r_stmt))
            elif isinstance(_l, bool):
                return self._OP_LAMBDA_MAP[self.op](_l, self.eval_bool(_r_stmt))
            elif isinstance(_l, int):
                return self._OP_LAMBDA_MAP[self.op](_l, self.eval_int(_r_stmt))
            elif isinstance(_l, str):
                # compare with Version?
                try:
                    _spec = self.eval_spec(self.op, _r_stmt)
                except ValueError:
                    return self._OP_LAMBDA_MAP[self.op](_l, self.eval_str(_r_stmt))
                else:
                    return _spec.match(Version(_l))
            else:
                raise_invalid_type_error()
        except KeyError:
            raise_invalid_type_error()

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
LEFT_VALUE = Word(alphas + nums + '${}_-.').setParseAction(lambda x: LeftValue(x[0]))

# Operators
_LE = Literal('<=')
_LT = Literal('<')

_GE = Literal('>=')
_GT = Literal('>')

_TILDE_EQ = Literal('~=')
_TILDE = Literal('~')

_CARET = Literal('^')

_EQ = Literal('==')
_NE = Literal('!=')
_VER_EQ = Literal('=')

_NOT_IN = Literal('not in')
_IN = Literal('in')

# sub-string operators should be defined after the main operators
OPERATORS = MatchFirst([
    _LE,
    _LT,
    _GE,
    _GT,
    _TILDE_EQ,
    _TILDE,
    _EQ,
    _NE,
    _VER_EQ,
    _CARET,
    _NOT_IN,
    _IN,
]).setParseAction(lambda x: x[0])

# Left Value is everything till the operator
STRING = _non_terminator_words.setParseAction(lambda x: Single(x[0]))
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
