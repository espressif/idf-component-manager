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

IF_IDF_VERSION_REGEX_COMPILED = re.compile(IF_IDF_VERSION_REGEX)
IF_TARGET_REGEX_COMPILED = re.compile(IF_TARGET_REGEX)


@serializable
class IfClause:
    _serialization_properties = [
        'clause',
        'bool_value',
    ]

    def __init__(self, clause, bool_value):  # type: (str, bool) -> None
        self.clause = clause
        self.bool_value = bool_value

    def __repr__(self):
        return '{} ({})'.format(self.clause, self.bool_value)

    @staticmethod
    def regex_str():
        if_idf_version = IF_IDF_VERSION_REGEX
        # remove the name group
        if_idf_version = re.sub(r'\(\?P<\w+>', '(?:', if_idf_version)
        # remove the first ^ and the last $ and make it as a group
        if_idf_version = '(' + if_idf_version[1:-1] + ')'

        if_target = IF_TARGET_REGEX
        # remove the name group
        if_target = re.sub(r'\(\?P<\w+>', '(?:', if_idf_version)
        # remove the first ^ and the last $ and make it as a group
        if_target = '(' + if_target[1:-1] + ')'

        return '^{}|{}$'.format(if_idf_version, if_target)


def _eval_str(s):  # type: (str) -> str
    _s = s.strip()
    if not (_s[0] == _s[-1] == '"'):
        _s = '"{}"'.format(_s.replace('"', r'\"'))

    try:
        return literal_eval(_s)
    except (ValueError, SyntaxError):
        raise SchemaError(None, 'Invalid string "{}" in "if" clause'.format(s))


def _eval_list(s):  # type: (str) -> list[str]
    _s = s.strip()

    if _s[0] == '[' and _s[-1] == ']':
        _s = _s[1:-1]

    try:
        return [_eval_str(part) for part in _s.split(',')]
    except (ValueError, SyntaxError):
        raise SchemaError(None, 'Invalid list "{}" in "if" clause'.format(s))


def _parse_if_idf_version_clause(mat):  # type: (re.Match) -> IfClause
    comparison = mat.group('comparison')
    spec = mat.group('spec')
    spec = ','.join([part.strip() for part in spec.split(',')])

    try:
        simple_spec = SimpleSpec('{}{}'.format(_eval_str(comparison), _eval_str(spec)))
    except ValueError:
        raise SchemaError(
            None, 'Invalid version specification for "idf_version": {clause}. Please use a format like '
            '"idf_version >=4.4,<5.3"\nDocumentation: '
            'https://docs.espressif.com/projects/idf-component-manager/en/latest/reference/manifest_file.html#rules'.
            format(clause=mat.string))

    try:
        idf_version = get_idf_version()
    except FetchingError:
        idf_version = None
        bool_value = False
    else:
        bool_value = simple_spec.match(Version(idf_version))

    return IfClause('{} {}'.format(idf_version, simple_spec.expression), bool_value)


def _parser_if_target_clause(mat):  # type: (re.Match) -> IfClause
    comparison = mat.group('comparison')
    targets = mat.group('targets').strip()

    try:
        env_target = get_env_idf_target()
    except ProcessingError:
        env_target = None
        bool_value = False
    else:
        if comparison == '!=':
            bool_value = env_target != _eval_str(targets)
        elif comparison == '==':
            bool_value = env_target == _eval_str(targets)
        elif comparison == 'not in':
            bool_value = env_target not in _eval_list(targets)
        elif comparison == 'in':
            bool_value = env_target in _eval_list(targets)
        else:
            raise SchemaError(
                None, 'Invalid if clause format for target: {clause}. You can specify rules based on target using '
                '"==", "!=", "in" or "not in" like: "target in [esp32, esp32c3]", "target == esp32"\n'
                'Documentation: '
                'https://docs.espressif.com/projects/idf-component-manager/en/latest/reference'
                '/manifest_file.html#rules'.format(clause=mat.string))

    return IfClause('{} {} {}'.format(env_target, comparison, targets), bool_value)


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
            clause=if_clause))
