import filecmp
import os
import shutil

from idf_component_manager.cmake_component_requirements import CMakeRequirementsManager, ComponentName

ORIGINAL_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    'component_requires_orig.temp.cmake',
)

MODIFIED_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    'component_requires.temp.cmake',
)


def test_e2e_cmake_requirements(tmp_path):
    result_path = os.path.join(tmp_path.as_posix(), 'component_requires.temp.cmake')
    shutil.copyfile(ORIGINAL_PATH, result_path)

    manager = CMakeRequirementsManager(result_path)
    requirements = manager.load()
    name = ComponentName('idf', 'espressif__cmp')
    requirements[name]['PRIV_REQUIRES'].append('abc')
    requirements[name]['REQUIRES'].append('def')
    manager.dump(requirements)

    assert filecmp.cmp(MODIFIED_PATH, result_path, shallow=False)
