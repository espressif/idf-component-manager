import os

from idf_component_tools.hash_tools import hash_dir, hash_file, hash_object, validate_dir


def fixture_path(id):
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'fixtures',
        'hash_examples',
        'component_%s' % id,
    )


class TestHashTools(object):
    def test_hash_object(self):
        obj = {'b': 2, 'a': {'b': 2, 'a': [1, 2, 3]}}
        expected_sha = '3767afa0787de5a1047a49694ee326ff375109eedba0c7cca052846991ceed03'

        assert hash_object(obj) == expected_sha

    def test_hash_file(self):
        file_path = os.path.join(fixture_path(1), '1.txt')
        expected_sha = '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b'

        assert hash_file(file_path) == expected_sha

    def test_hash_dir(self):
        expected_sha = '299e78217cd6cb4f6962dde0de8c34a8aa8df7c80d8ac782d1944a4ec5b0ff8e'
        assert hash_dir(fixture_path(1)) == expected_sha

    def test_hash_dir_ignore(self):
        expected_sha = '299e78217cd6cb4f6962dde0de8c34a8aa8df7c80d8ac782d1944a4ec5b0ff8e'

        assert hash_dir(
            fixture_path(4), exclude=[
                '**/ignore.dir/*',
                '**/*.me',
            ]) == expected_sha

    def test_hash_not_equal(self):
        expected_sha = '299e78217cd6cb4f6962dde0de8c34a8aa8df7c80d8ac782d1944a4ec5b0ff8e'

        assert validate_dir(fixture_path(1), expected_sha)
        assert validate_dir(
            fixture_path(4),
            expected_sha,
            exclude=[
                '**/ignore.dir/*',
                '**/*.me',
            ],
        )
        assert not validate_dir(fixture_path(2), expected_sha)
        assert not validate_dir(fixture_path(3), expected_sha)
        assert not validate_dir(fixture_path(4), expected_sha)
