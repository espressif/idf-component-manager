# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os

from idf_component_tools.hash_tools.calculate import hash_dir, hash_file, hash_object


class TestHashTools(object):
    def test_hash_object(self):
        obj = {'b': 2, 'a': {'b': 2, 'a': [1, 2, 3]}}
        expected_sha = '3767afa0787de5a1047a49694ee326ff375109eedba0c7cca052846991ceed03'

        assert hash_object(obj) == expected_sha

    def test_hash_file(self, hash_component):
        file_path = os.path.join(hash_component(1), '1.txt')
        expected_sha = '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b'

        assert hash_file(file_path) == expected_sha

    def test_hash_dir(self, hash_component):
        expected_sha = '299e78217cd6cb4f6962dde0de8c34a8aa8df7c80d8ac782d1944a4ec5b0ff8e'
        assert hash_dir(hash_component(1)) == expected_sha

    def test_hash_dir_ignore(self, hash_component):
        expected_sha = '299e78217cd6cb4f6962dde0de8c34a8aa8df7c80d8ac782d1944a4ec5b0ff8e'

        assert (
            hash_dir(
                hash_component(4),
                exclude=[
                    '**/ignore.dir/*',
                    '**/*.me',
                ],
            )
            == expected_sha
        )

    def test_hash_dir_include_exclude(self, hash_component):
        expected_sha = '299e78217cd6cb4f6962dde0de8c34a8aa8df7c80d8ac782d1944a4ec5b0ff8e'

        assert (
            hash_dir(
                hash_component(4),
                exclude=[
                    '**/*',
                ],
                include=[
                    '1.txt',
                ],
            )
            == expected_sha
        )
