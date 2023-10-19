# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_manager.utils import print_error, print_hint, print_info, print_warn


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
