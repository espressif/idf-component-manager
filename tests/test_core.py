# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from idf_component_manager.core import get_processing_timeout


def test_env_job_timeout_empty(monkeypatch):
    monkeypatch.setenv('COMPONENT_MANAGER_JOB_TIMEOUT', 300)
    assert get_processing_timeout() == 300
