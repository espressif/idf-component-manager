import os

import pytest
from semantic_version import Version

from component_manager.utils.git_client import GitClient, GitFatalError


class TestGitClient(object):
    def test_run(self):
        git = GitClient(git_command=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fake_git.py'))

        output = git.run(['clone', 'https://github.com/espressif/esp-idf', 'test-path'])

        assert "Cloning into 'test-path'..." in output

    def test_version(self):
        git = GitClient(git_command=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fake_git.py'))
        assert git.version() == Version('2.21.0')

        bad_git = GitClient(git_command=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fake_bad_git.py'))
        with pytest.raises(GitFatalError):
            bad_git.version()

    def test_check_version(self):
        git = GitClient(git_command=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fake_git.py'))

        assert git.check_version('2.12.0')

        with pytest.raises(GitFatalError) as e:
            git.check_version('2.42.1')
        assert '2.21.0 is older' in str(e.value)
