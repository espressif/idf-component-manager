# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_manager.utils import (
    ComponentType,
    print_error,
    print_hint,
    print_info,
    print_warn,
)


class TestUtils(object):
    def test_print_error_string(self, capsys):
        print_error('Hello')
        captured = capsys.readouterr()

        assert '' == captured.out
        assert 'ERROR: Hello\n' == captured.err

    def test_print_error_exception(self, capsys):
        print_error(Exception('test exception'))
        captured = capsys.readouterr()

        assert '' == captured.out
        assert 'ERROR: test exception\n' in captured.err

    def test_print_warning(self, capsys):
        print_warn('Hello')
        captured = capsys.readouterr()

        assert '' == captured.out
        assert 'WARNING: Hello\n' == captured.err

    def test_print_hint(self, capsys):
        print_hint('Hello')
        captured = capsys.readouterr()

        assert 'HINT: Hello\n' == captured.out
        assert '' == captured.err

    def test_print_message(self, capsys):
        print_info('Hello')
        captured = capsys.readouterr()

        assert 'Hello\n' == captured.out
        assert '' == captured.err


class TestComponentType(object):
    def test_component_type_order(self):
        assert (
            ComponentType.IDF_COMPONENTS
            < ComponentType.PROJECT_MANAGED_COMPONENTS
            < ComponentType.PROJECT_COMPONENTS
            < ComponentType.PROJECT_EXTRA_COMPONENTS
        )
        assert (
            ComponentType.PROJECT_EXTRA_COMPONENTS
            > ComponentType.PROJECT_COMPONENTS
            > ComponentType.PROJECT_MANAGED_COMPONENTS
            > ComponentType.IDF_COMPONENTS
        )

    def test_component_type_equality(self):
        assert (
            ComponentType.IDF_COMPONENTS
            != ComponentType.PROJECT_MANAGED_COMPONENTS
            != ComponentType.PROJECT_COMPONENTS
            != ComponentType.PROJECT_EXTRA_COMPONENTS
        )

        assert ComponentType.IDF_COMPONENTS == ComponentType('"idf_components"')
        assert ComponentType.PROJECT_MANAGED_COMPONENTS == ComponentType(
            '"project_managed_components"'
        )
        assert ComponentType.PROJECT_COMPONENTS == ComponentType('"project_components"')
        assert ComponentType.PROJECT_EXTRA_COMPONENTS == ComponentType('"project_extra_components"')

    def test_component_type_equality_str(self):
        assert ComponentType.IDF_COMPONENTS == '"idf_components"'
        assert ComponentType.PROJECT_MANAGED_COMPONENTS == '"project_managed_components"'
        assert ComponentType.PROJECT_COMPONENTS == '"project_components"'
        assert ComponentType.PROJECT_EXTRA_COMPONENTS == '"project_extra_components"'
