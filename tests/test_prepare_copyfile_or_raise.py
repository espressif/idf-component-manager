# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import shutil

import pytest

from idf_component_manager.prepare_components.prepare import _copyfile_or_raise
from idf_component_tools.errors import FatalError


def test_copyfile_or_raise_copies_file(tmp_path):
    src = tmp_path / 'src.txt'
    dst = tmp_path / 'dst.txt'

    src.write_text('hello', encoding='utf-8')

    _copyfile_or_raise(src, dst, action='copy')

    assert dst.read_text(encoding='utf-8') == 'hello'


def test_copyfile_or_raise_raises_fatalerror(monkeypatch, tmp_path):
    src = tmp_path / 'src.txt'
    dst = tmp_path / 'dst.txt'

    def _boom(*_args, **_kwargs):
        raise OSError('boom')

    monkeypatch.setattr(shutil, 'copyfile', _boom)

    with pytest.raises(FatalError) as excinfo:
        _copyfile_or_raise(src, dst, action='copy')

    msg = str(excinfo.value)
    assert 'Failed to copy' in msg
    assert str(src) in msg
    assert str(dst) in msg
    assert 'boom' in msg
