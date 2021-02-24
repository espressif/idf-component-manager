from idf_component_tools.file_tools import copytree_ignore_builder


class TestFileTools(object):
    def test_hash_object(self):
        ignore = copytree_ignore_builder()
        assert ignore('.git', ['a.py', 'b.py', 'c.pyc']) == set([])

        ignore = copytree_ignore_builder()
        assert ignore('some', ['a.py', 'b.py', 'c.pyc', 'pyc.dir']) == set(['a.py', 'b.py', 'pyc.dir'])
