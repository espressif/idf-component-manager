import os
import shutil
import tempfile

from idf_component_manager.core import ComponentManager


def test_init_project():
    tempdir = tempfile.mkdtemp()
    try:
        manifest_path = os.path.join(tempdir, 'idf_project.yml')
        manager = ComponentManager(path=tempdir)

        manager.init_project()

        with open(manifest_path, 'r') as f:
            assert f.readline().startswith('## IDF Component Manager')

    finally:
        shutil.rmtree(tempdir)
