# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os

import psutil


def get_cmake_pid() -> int:
    """Find the PID of the CMake process that initiated this build.

    This script is invoked multiple times during a single CMake build
    (prepare_dependencies, inject_requirements). On Linux and macOS,
    os.getppid() consistently returns the same parent PID across invocations.

    On Windows, however, each invocation of this script is spawned through a
    new intermediate process (e.g. cmd.exe), so os.getppid() returns a different
    PID each time. This causes multiple state files to be created instead of
    sharing one per CMake build, breaking the run counter and component list logic.

    This function walks up the process tree to find the CMake process itself,
    which remains constant throughout the build, ensuring consistent state file
    naming across all invocations.

    Returns:
        The PID of the CMake parent process, or os.getppid() as a fallback
        if no CMake process is found in the ancestry.
    """

    current = psutil.Process()
    parent = current.parent()
    while parent is not None:
        if 'cmake' in parent.name().lower():
            return parent.pid
        parent = parent.parent()

    return os.getppid()
