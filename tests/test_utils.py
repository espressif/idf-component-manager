# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_manager.utils import error, info, warn


class TestUtils(object):
    def test_print_error_string(self, capsys):
        error('Hello')
        captured = capsys.readouterr()

        assert '' == captured.out
        assert 'ERROR: Hello\n' == captured.err

    def test_print_error_exception(self, capsys):
        error(Exception('test exception'))
        captured = capsys.readouterr()

        assert '' == captured.out
        assert 'ERROR: test exception\n' in captured.err

    def test_print_warning(self, capsys):
        warn('Hello')
        captured = capsys.readouterr()

        assert '' == captured.out
        assert 'WARNING: Hello\n' == captured.err

    def test_print_message(self, capsys):
        info('Hello')
        captured = capsys.readouterr()

        assert 'Hello\n' == captured.out
        assert '' == captured.err
