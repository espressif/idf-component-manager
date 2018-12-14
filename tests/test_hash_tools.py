import os

from component_manager.lock import HashTools


def fixture_path(id):
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        "fixtures",
        "hash_examples",
        "component_%s" % id,
    )


class TestHashTools(object):
    def test_hash_file(self):
        file_path = os.path.join(fixture_path(1), "1.txt")
        expected_sha = (
            "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b"
        )

        assert HashTools.hash_file(file_path) == expected_sha

    def test_hash_dir(self):
        expected_sha = (
            "2fc3be7897ed4c389941026d8f9e44c67c0b81154827d2578f790739e321670d"
        )
        assert HashTools.hash_dir(fixture_path(1)) == expected_sha

    def test_hash_dir_ignore(self):
        expected_sha = (
            "2fc3be7897ed4c389941026d8f9e44c67c0b81154827d2578f790739e321670d"
        )

        assert (
            HashTools.hash_dir(
                fixture_path(4), ignored_dirs=["ignore.dir"], ignored_files=["*.me"]
            )
            == expected_sha
        )

    def test_hash_not_equal(self):
        expected_sha = (
            "2fc3be7897ed4c389941026d8f9e44c67c0b81154827d2578f790739e321670d"
        )

        assert HashTools.validate(fixture_path(1), expected_sha)
        assert HashTools.validate(
            fixture_path(4),
            expected_sha,
            ignored_dirs=["ignore.dir"],
            ignored_files=["*.me"],
        )
        assert not HashTools.validate(fixture_path(2), expected_sha)
        assert not HashTools.validate(fixture_path(3), expected_sha)
        assert not HashTools.validate(fixture_path(4), expected_sha)
