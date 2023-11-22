# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path

from .calculate import hash_dir

try:
    from typing import Any, Iterable, Text
except ImportError:
    pass


def validate_dir(
    root,  # type: Text | Path
    dir_hash,  # type: Text
    include=None,  # type Iterable[Text] | None
    exclude=None,  # type: Iterable[Text] | None
    exclude_default=True,  # type: bool
):
    # type: (...) -> bool
    """Check if directory hash is the same as provided"""
    current_hash = Path(root).is_dir() and hash_dir(
        root, include=include, exclude=exclude, exclude_default=exclude_default
    )
    return current_hash == dir_hash
