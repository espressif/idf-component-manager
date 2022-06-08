# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_tools import semver
from idf_component_tools.__version__ import __version__

# IDF Component Version is the same as tools
version = semver.Version(__version__)
