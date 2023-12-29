# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

from idf_component_tools.registry.request_processor import verify_ssl

CA_MAPPING = {
    'example.com': 'example.com.crt',
}


def test_verify_ssl_without_ssl_verification(monkeypatch):
    # Disable SSL verification
    monkeypatch.setenv('IDF_COMPONENT_VERIFY_SSL', '0')
    assert verify_ssl('https://example.com') == False


def test_verify_ssl_with_known_root_ca_file():
    endpoint = 'https://example.com'
    result = verify_ssl(endpoint, CA_MAPPING)
    assert result.endswith(os.path.join('certs', 'example.com.crt'))


def test_verify_ssl_with_unknown_root_ca_file():
    endpoint = 'https://unknown.com'
    result = verify_ssl(endpoint, CA_MAPPING)
    assert result == True
