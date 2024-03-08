# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t
from pathlib import Path

from .calculate import hash_dir


def validate_dir(
    root: t.Union[str, Path],
    dir_hash: str,
    include: t.Optional[t.Iterable[str]] = None,
    exclude: t.Optional[t.Iterable[str]] = None,
    exclude_default: bool = True,
) -> bool:
    """Check if directory hash is the same as provided"""
    current_hash = Path(root).is_dir() and hash_dir(
        root, include=include, exclude=exclude, exclude_default=exclude_default
    )
    return current_hash == dir_hash
