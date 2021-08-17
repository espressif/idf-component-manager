import pytest

from idf_component_manager.version_solver.helper import PackageSource


@pytest.fixture()
def source():
    return PackageSource()
