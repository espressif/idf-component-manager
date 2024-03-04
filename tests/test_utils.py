# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_manager.utils import (
    ComponentSource,
    print_error,
    print_hint,
    print_info,
    print_warn,
)


class TestUtils:
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


class TestComponentSource:
    def test_component_source_order(self):
        assert (
            ComponentSource.IDF_COMPONENTS
            < ComponentSource.PROJECT_MANAGED_COMPONENTS
            < ComponentSource.PROJECT_EXTRA_COMPONENTS
            < ComponentSource.PROJECT_COMPONENTS
        )
        assert (
            ComponentSource.PROJECT_COMPONENTS
            > ComponentSource.PROJECT_EXTRA_COMPONENTS
            > ComponentSource.PROJECT_MANAGED_COMPONENTS
            > ComponentSource.IDF_COMPONENTS
        )

    def test_component_source_equality(self):
        assert (
            ComponentSource.IDF_COMPONENTS
            != ComponentSource.PROJECT_MANAGED_COMPONENTS
            != ComponentSource.PROJECT_COMPONENTS
            != ComponentSource.PROJECT_EXTRA_COMPONENTS
        )

        assert ComponentSource.IDF_COMPONENTS == ComponentSource('"idf_components"')
        assert ComponentSource.PROJECT_MANAGED_COMPONENTS == ComponentSource(
            '"project_managed_components"'
        )
        assert ComponentSource.PROJECT_COMPONENTS == ComponentSource('"project_components"')
        assert ComponentSource.PROJECT_EXTRA_COMPONENTS == ComponentSource(
            '"project_extra_components"'
        )

    def test_component_source_equality_str(self):
        assert ComponentSource.IDF_COMPONENTS == '"idf_components"'
        assert ComponentSource.PROJECT_MANAGED_COMPONENTS == '"project_managed_components"'
        assert ComponentSource.PROJECT_COMPONENTS == '"project_components"'
        assert ComponentSource.PROJECT_EXTRA_COMPONENTS == '"project_extra_components"'
