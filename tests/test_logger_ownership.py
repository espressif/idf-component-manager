# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Logger ownership: extension setup must not claim EspLog.instance."""

import pytest
from esp_pylib.logger import EspLog

from idf_component_tools.errors import WarningAsExceptionError
from idf_component_tools.logging import configure_extension_logging, setup_logging
from idf_component_tools.messages import configure_message_flags, hint, warn


@pytest.fixture(autouse=True)
def _reset_message_flags():
    """Keep message policy isolated between tests in this module."""
    configure_message_flags(no_hints=False, warnings_as_errors=False)
    yield
    configure_message_flags(no_hints=False, warnings_as_errors=False)


def test_configure_extension_logging_preserves_esp_log(monkeypatch, recording_log):
    monkeypatch.setenv('IDF_COMPONENT_NO_HINTS', '1')
    EspLog._reset()
    host = EspLog()
    EspLog.set_logger(host)

    configure_extension_logging()

    assert EspLog.instance is host
    assert type(EspLog.instance) is EspLog

    # Policy applies through messages wrappers even when host is not a CM logger.
    EspLog.set_logger(recording_log)
    recording_log.clear()
    hint('should be suppressed')
    assert recording_log.records == []


def test_configure_extension_logging_preserves_foreign_esp_log_subclass(monkeypatch, recording_log):
    """Host may be EsptoolLogger (or any EspLog subclass); CM must leave it alone."""

    class HostToolLog(EspLog):
        pass

    monkeypatch.setenv('IDF_COMPONENT_NO_HINTS', '1')
    EspLog._reset()
    if 'instance' in HostToolLog.__dict__:
        del HostToolLog.instance
    host = HostToolLog()
    EspLog.set_logger(host)

    configure_extension_logging()

    assert EspLog.instance is host
    assert isinstance(EspLog.instance, HostToolLog)

    EspLog.set_logger(recording_log)
    recording_log.clear()
    hint('should be suppressed under foreign logger')
    assert recording_log.records == []


def test_configure_extension_logging_preserves_real_esptool_logger(monkeypatch):
    esptool_logger = pytest.importorskip('esptool.logger')
    EsptoolLogger = esptool_logger.EsptoolLogger

    monkeypatch.setenv('IDF_COMPONENT_NO_HINTS', '1')
    EspLog._reset()
    if 'instance' in EsptoolLogger.__dict__:
        del EsptoolLogger.instance
    host = EsptoolLogger()
    EspLog.set_logger(host)

    configure_extension_logging()

    assert EspLog.instance is host
    assert isinstance(EspLog.instance, EsptoolLogger)


def test_configure_extension_logging_does_not_apply_debug_mode(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_DEBUG_MODE', '1')
    EspLog._reset()
    host = EspLog()
    host.set_verbosity(1)  # NORMAL
    EspLog.set_logger(host)

    configure_extension_logging()

    assert EspLog.instance is host
    assert host._verbosity == 1


def test_setup_logging_installs_esp_log(monkeypatch):
    monkeypatch.delenv('IDF_COMPONENT_DEBUG_MODE', raising=False)
    monkeypatch.delenv('IDF_COMPONENT_NO_HINTS', raising=False)
    EspLog._reset()

    setup_logging()

    assert type(EspLog.instance) is EspLog


def test_warnings_as_errors_via_message_flags():
    configure_message_flags(no_hints=False, warnings_as_errors=True)
    with pytest.raises(WarningAsExceptionError, match='boom'):
        warn('boom')


def test_setup_logging_sets_warnings_as_errors(monkeypatch):
    monkeypatch.delenv('IDF_COMPONENT_NO_HINTS', raising=False)
    EspLog._reset()
    setup_logging(warnings_as_errors=True)
    with pytest.raises(WarningAsExceptionError, match='oops'):
        warn('oops')


def test_setup_logging_emits_truststore_debug(monkeypatch, recording_log):
    monkeypatch.setenv('IDF_COMPONENT_DEBUG_MODE', '1')
    EspLog._reset()
    setup_logging()
    # setup_logging replaces the recorder; re-check via a second call path
    EspLog.set_logger(recording_log)
    recording_log.clear()
    from idf_component_tools.logging import _log_truststore_status

    _log_truststore_status()
    assert any('truststore' in r.message or 'certifi' in r.message for r in recording_log.records)


def test_log_truststore_status_skips_when_no_logger():
    EspLog._reset()
    from idf_component_tools.logging import _log_truststore_status

    _log_truststore_status()
    assert EspLog.instance is None
