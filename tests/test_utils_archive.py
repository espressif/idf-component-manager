class TestUtilsArchive(object):
    def test_get_format_from_path(self):
        from component_manager.utils.archive import get_format_from_path

        assert get_format_from_path("sdf") is None
        assert get_format_from_path("sdf.tar") == ("tar", "tar")
        assert get_format_from_path("sdf.tgz") == ("gztar", "tgz")
        assert get_format_from_path("sdf.tar.gz") == ("gztar", "tgz")
        assert get_format_from_path("sdf.zip") == ("zip", "zip")

    def test_is_known_format(self):
        from component_manager.utils.archive import is_known_format

        assert not is_known_format("sdf")
        assert is_known_format("tar")
        assert is_known_format("zip")
        assert is_known_format("gztar")
