# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import sys

from idf_component_tools.environment import ComponentManagerSettings

logger = logging.getLogger(__package__)
if ComponentManagerSettings().DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))
