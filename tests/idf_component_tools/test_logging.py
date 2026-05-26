# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

import pytest
from esp_pylib.logger import EspLog, Verbosity, log

from idf_component_tools import debug, error, hint, notice, setup_logging, warn
from idf_component_tools.errors import WarningAsExceptionError
from idf_component_tools.logging import ComponentManagerLog, suppress_logging


@pytest.fixture
def real_logger():
    """Temporarily replace the autouse RecordingLog with the real ComponentManagerLog.

    The autouse fixture in conftest installs a capturing recorder for assertion
    convenience; tests in this module want to exercise the real logger machinery
    instead.
    """
    EspLog._reset()
    ComponentManagerLog._reset()
    try:
        yield
    finally:
        EspLog._reset()
        ComponentManagerLog._reset()


class TestSetupLogging:
    def test_installs_component_manager_log(self, real_logger):  # noqa: ARG002
        setup_logging()
        assert isinstance(EspLog.instance, ComponentManagerLog)

    def test_debug_mode_enables_verbose(self, real_logger, monkeypatch):  # noqa: ARG002
        monkeypatch.setenv('IDF_COMPONENT_DEBUG_MODE', '1')
        setup_logging()
        assert EspLog.instance._verbosity == Verbosity.VERBOSE  # type: ignore[union-attr]

    def test_default_mode_is_normal(self, real_logger, monkeypatch):  # noqa: ARG002
        monkeypatch.delenv('IDF_COMPONENT_DEBUG_MODE', raising=False)
        setup_logging()
        assert EspLog.instance._verbosity == Verbosity.NORMAL  # type: ignore[union-attr]

    def test_no_hints_env_suppresses_hint_output(self, real_logger, monkeypatch):  # noqa: ARG002
        monkeypatch.setenv('IDF_COMPONENT_NO_HINTS', '1')
        monkeypatch.delenv('IDF_COMPONENT_DEBUG_MODE', raising=False)
        setup_logging()
        with patch.object(EspLog, 'hint') as mock_hint:
            hint('this should be silenced')
            mock_hint.assert_not_called()

    def test_debug_mode_overrides_no_hints(self, real_logger, monkeypatch):  # noqa: ARG002
        # Hints are always useful while debugging, so DEBUG_MODE wins over NO_HINTS.
        monkeypatch.setenv('IDF_COMPONENT_NO_HINTS', '1')
        monkeypatch.setenv('IDF_COMPONENT_DEBUG_MODE', '1')
        setup_logging()
        with patch.object(EspLog, 'hint') as mock_hint:
            hint('shown in debug mode')
            mock_hint.assert_called_once_with('shown in debug mode')

    def test_hints_delegate_to_esp_pylib_when_enabled(self, real_logger, monkeypatch):  # noqa: ARG002
        monkeypatch.delenv('IDF_COMPONENT_NO_HINTS', raising=False)
        setup_logging()
        with patch.object(EspLog, 'hint') as mock_hint:
            hint('payload')
            mock_hint.assert_called_once_with('payload')


class TestWarningsAsErrors:
    def test_warn_raises_when_enabled(self, real_logger):  # noqa: ARG002
        setup_logging(warnings_as_errors=True)
        with pytest.raises(WarningAsExceptionError, match='boom'):
            warn('boom')

    def test_warn_does_not_raise_by_default(self, real_logger):  # noqa: ARG002
        setup_logging(warnings_as_errors=False)
        with patch.object(ComponentManagerLog, 'note'):
            # Should not raise; just call through to super().warn
            warn('normal warning')


class TestSuppressLogging:
    def test_silences_then_restores(self, real_logger):  # noqa: ARG002
        setup_logging()
        previous = EspLog.instance._verbosity  # type: ignore[union-attr]
        with suppress_logging():
            assert EspLog.instance._verbosity == Verbosity.SILENT  # type: ignore[union-attr]
        assert EspLog.instance._verbosity == previous  # type: ignore[union-attr]

    def test_level_param_accepted_and_still_silences(self, real_logger):  # noqa: ARG002
        setup_logging()
        previous = EspLog.instance._verbosity  # type: ignore[union-attr]
        with suppress_logging(50):
            assert EspLog.instance._verbosity == Verbosity.SILENT  # type: ignore[union-attr]
        assert EspLog.instance._verbosity == previous  # type: ignore[union-attr]


class TestLegacyApiReexports:
    def test_symbols_are_importable(self):
        import logging

        from idf_component_tools import HINT_LEVEL, LOGGING_NAMESPACE, get_logger

        assert HINT_LEVEL == 15
        assert LOGGING_NAMESPACE == 'idf_component_tools'
        logger = get_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'idf_component_tools'


class TestIdeWebSocketForwarding:
    """Verify the inherited IDE WebSocket forwarding still fires for warn/err."""

    def test_warn_forwards_when_ws_enabled(self, real_logger, monkeypatch):  # noqa: ARG002
        setup_logging()
        monkeypatch.setattr('esp_pylib.logger._ws_is_enabled', lambda: True)
        with patch('esp_pylib.logger.send_log_message') as mock_send:
            warn('hello')
            assert mock_send.called
            assert mock_send.call_args.args[0] == 'warning'
            assert mock_send.call_args.args[1] == 'hello'

    def test_err_forwards_when_ws_enabled(self, real_logger, monkeypatch):  # noqa: ARG002
        setup_logging()
        monkeypatch.setattr('esp_pylib.logger._ws_is_enabled', lambda: True)
        with patch('esp_pylib.logger.send_log_message') as mock_send:
            error('boom')
            assert mock_send.called
            assert mock_send.call_args.args[0] == 'error'
            assert mock_send.call_args.args[1] == 'boom'

    def test_notice_does_not_forward(self, real_logger, monkeypatch):  # noqa: ARG002
        setup_logging()
        monkeypatch.setattr('esp_pylib.logger._ws_is_enabled', lambda: True)
        with patch('esp_pylib.logger.send_log_message') as mock_send:
            notice('info')
            assert not mock_send.called


class TestLogProxy:
    def test_proxy_delegates_to_installed_singleton(self, real_logger):  # noqa: ARG002
        setup_logging()
        assert log.__class__.__name__ == '_LogProxy'  # type: ignore[attr-defined]
        # Touch an attribute to make sure delegation works.
        assert callable(log.warn)


class TestMarkupEscaping:
    """Messages must be escaped so Rich markup in dynamic content is shown literally.

    esp-pylib renders log messages as Rich markup and does not escape, so before the
    escape in ``_fmt`` ``[abc]`` was silently swallowed and ``[/]`` raised
    ``rich.errors.MarkupError``.  The pre-migration stdlib logger treated messages as
    plain text; escaping restores that behaviour.
    """

    def test_fmt_escapes_square_brackets(self):
        from idf_component_tools.messages import _fmt

        assert _fmt('Path [abc]', ()) == r'Path \[abc]'

    def test_fmt_formats_before_escaping(self):
        from idf_component_tools.messages import _fmt

        assert _fmt('name %s', ('[abc]',)) == r'name \[abc]'

    def test_fmt_passes_non_string_through(self):
        from idf_component_tools.messages import _fmt

        # Some callers pass a None message (e.g. an empty upload status); escaping
        # must not choke on it.
        assert _fmt(None, ()) is None  # type: ignore[arg-type]

    def test_malformed_markup_does_not_raise(self, real_logger):  # noqa: ARG002
        setup_logging()
        # Both lines would raise rich.errors.MarkupError before _fmt escaped them.
        error('foo[/]bar')
        notice('Path [abc]')


class TestKwargsBackwardsCompat:
    """Helpers must not raise when called with stdlib logging kwargs.

    Before the esp-pylib migration the helpers accepted ``**kwargs`` and forwarded
    them to the stdlib logger.  After the migration the signatures were narrowed to
    ``*args`` only, causing ``TypeError`` for any caller that passed e.g.
    ``exc_info=True``.  The fix restores ``**kwargs`` and silently ignores them.
    """

    def test_error_with_exc_info_does_not_raise(self, recording_log):
        error('boom', exc_info=True)
        assert any(r.level == 'error' and r.message == 'boom' for r in recording_log.records)

    def test_warn_with_stacklevel_does_not_raise(self, recording_log):
        warn('w %s', 'x', stacklevel=2)
        assert any(r.level == 'warning' and r.message == 'w x' for r in recording_log.records)

    def test_debug_with_extra_does_not_raise(self, recording_log):
        debug('dbg', extra={'key': 'val'})
        assert any(r.level == 'debug' and r.message == 'dbg' for r in recording_log.records)

    def test_hint_with_kwargs_does_not_raise(self, recording_log):
        hint('hnt', stacklevel=1)
        assert any(r.level == 'hint' and r.message == 'hnt' for r in recording_log.records)

    def test_notice_with_kwargs_does_not_raise(self, recording_log):
        notice('ntc', exc_info=False)
        assert any(r.level == 'notice' and r.message == 'ntc' for r in recording_log.records)
