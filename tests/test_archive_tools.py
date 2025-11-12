# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import tarfile
import tempfile
from filecmp import dircmp

import pytest

from idf_component_tools.archive_tools import (
    ArchiveError,
    get_format_from_path,
    is_known_format,
    pack_archive,
    unpack_archive,
    unpack_tar,
    unpack_zip,
)


@pytest.fixture
def archive_path(fixtures_path):
    def inner(ext):
        return os.path.join(
            fixtures_path,
            'archives',
            f'cmp_1.0.0.{ext}',
        )

    return inner


class TestUtilsArchive:
    def test_get_format_from_path(self):
        with pytest.raises(ArchiveError):
            get_format_from_path('sdf')
        assert get_format_from_path('sdf.tar') == ('tar', 'tar', unpack_tar)
        assert get_format_from_path('sdf.tgz') == ('gztar', 'tgz', unpack_tar)
        assert get_format_from_path('sdf.tar.gz') == ('gztar', 'tgz', unpack_tar)
        assert get_format_from_path('sdf.zip') == ('zip', 'zip', unpack_zip)

    def test_is_known_format(self):
        assert not is_known_format('sdf')
        assert is_known_format('tar')
        assert is_known_format('zip')
        assert is_known_format('gztar')

    @pytest.mark.parametrize(
        ['ext', 'func'],
        [
            ('tar.gz', unpack_tar),
            ('zip', unpack_zip),
        ],
    )
    def test_unpack_archive_tgz(self, ext, func, archive_path, tmp_path):
        target = tmp_path / 'cmp'

        func(archive_path(ext), str(target))

        assert (target / 'CMakeLists.txt').is_file()
        assert (target / 'include').is_dir()
        assert (target / 'include' / 'cmp.h').is_file()

    def test_unpack_archive(self, archive_path):
        tempdir = tempfile.mkdtemp()
        target1 = os.path.join(tempdir, 'cmp_1')
        target2 = os.path.join(tempdir, 'cmp_2')

        try:
            unpack_archive(archive_path('zip'), target1)
            unpack_archive(archive_path('tar.gz'), target2)

            assert os.path.isfile(os.path.join(target1, 'CMakeLists.txt'))
            assert os.path.isfile(os.path.join(target2, 'CMakeLists.txt'))
            assert dircmp(target1, target2)

        finally:
            shutil.rmtree(tempdir)

    def test_pack_archive_creates_valid_relative_tar(self, tmp_path):
        source_dir = tmp_path / 'test_component'
        source_dir.mkdir()
        (source_dir / 'file.txt').touch()
        archive_file = tmp_path / 'archive'
        pack_archive(source_dir, archive_file)

        assert archive_file.exists()

        with tarfile.open(archive_file, 'r:gz') as tar:
            names = tar.getnames()

        # Verify: no absolute paths, files stored at top-level (relative './')
        assert all(not n.startswith('/') for n in names)
        assert './file.txt' in names
