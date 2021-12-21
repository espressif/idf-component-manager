from idf_component_tools import sources


class TestValidateGitSource(object):
    def test_validate_version_spec_git(self, valid_manifest):
        source = sources.GitSource({'git': ''})
        assert source.validate_version_spec('feature/new_test_branch')
        assert source.validate_version_spec('test_branch')
        assert source.validate_version_spec('38041fa9e7f8a79b8ff8cd247c73cf92b7e3c23e')
        assert not source.validate_version_spec('..non_valid_branch')
        assert not source.validate_version_spec('@{non_valid_too')
        assert not source.validate_version_spec('wrong\\slash')
