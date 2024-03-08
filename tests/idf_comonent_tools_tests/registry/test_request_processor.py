# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_tools.registry.request_processor import verify_ssl


def test_verify_ssl_without_ssl_verification(monkeypatch):
    # Disable SSL verification
    monkeypatch.setenv('IDF_COMPONENT_VERIFY_SSL', '0')
    assert verify_ssl() == False


def test_verify_ssl():
    assert verify_ssl()
