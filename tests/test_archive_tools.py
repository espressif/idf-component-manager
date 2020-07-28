import os
import shutil
import tempfile
from filecmp import dircmp

import pytest
from idf_component_tools.archive_tools import (
    ArchiveError, get_format_from_path, is_known_format, unpack_archive, unpack_tar, unpack_zip)


def archive_path(ext):
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'fixtures',
        'archives',
        'cmp_1.0.0.%s' % ext,
    )


class TestUtilsArchive(object):
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

    def test_unpack_archive_tgz(self):

        tempdir = tempfile.mkdtemp()
        target = os.path.join(tempdir, 'cmp')

        try:

            unpack_tar(archive_path('tar.gz'), target)

            assert os.path.isfile(os.path.join(target, 'CMakeLists.txt'))
            assert os.path.isdir(os.path.join(target, 'include'))
            assert os.path.isfile(os.path.join(target, 'include', 'cmp.h'))

        finally:
            shutil.rmtree(tempdir)

    def test_unpack_archive_zip(self):
        tempdir = tempfile.mkdtemp()
        target = os.path.join(tempdir, 'cmp')

        try:
            unpack_zip(archive_path('zip'), target)

            assert os.path.isfile(os.path.join(target, 'CMakeLists.txt'))
            assert os.path.isdir(os.path.join(target, 'include'))
            assert os.path.isfile(os.path.join(target, 'include', 'cmp.h'))

        finally:
            shutil.rmtree(tempdir)

    def test_unpack_archive(self):
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
