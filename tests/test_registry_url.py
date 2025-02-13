# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import textwrap

import pytest

from idf_component_tools.config import config_file
from idf_component_tools.errors import NoSuchProfile
from idf_component_tools.sources import WebServiceSource


def test_set_by_env_var(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', 'https://foo.com')
    source = WebServiceSource()
    assert source.registry_url == 'https://foo.com'

    source = WebServiceSource(registry_url='https://bar.com')
    assert source.registry_url == 'https://bar.com'


def test_set_by_profile(
    monkeypatch,
    isolate_idf_component_manager_yml,  # noqa: ARG001
):
    monkeypatch.setenv('IDF_COMPONENT_PROFILE', 'notexist')
    with pytest.raises(NoSuchProfile):
        WebServiceSource()

    config_file().write_text(
        textwrap.dedent("""
    profiles:
      default:
        registry_url: https://foo.com

      bar:
        registry_url: https://bar.com
    """)
    )

    monkeypatch.delenv('IDF_COMPONENT_PROFILE')
    source = WebServiceSource()
    assert source.registry_url == 'https://foo.com/'

    monkeypatch.setenv('IDF_COMPONENT_PROFILE', 'bar')
    source = WebServiceSource()
    assert source.registry_url == 'https://bar.com/'

    source = WebServiceSource(registry_url='https://baz.com')
    assert source.registry_url == 'https://baz.com'
