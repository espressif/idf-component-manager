import os
import shutil
from tempfile import mkdtemp

import pytest
import yaml
from distutils.dir_util import copy_tree
from idf_component_manager.core import ComponentManager


def include_library(project_path, library):
    source_path = os.path.join(project_path, "main", "main.c")
    with open(source_path, "r+") as source_file:
        content = source_file.read()
        source_file.seek(0, 0)
        source_file.write('#include "' + library + '"\n')
        source_file.write(content)


def add_dependency_to_manifest(project_path, dependencies, library):
    with open(os.path.join(project_path, "main", "idf_component.yml")) as manifest:
        manifest_dict = yaml.safe_load(manifest)
    manifest_dict['dependencies'][library] = dependencies[library]

    with open(os.path.join(project_path, "main", "idf_component.yml"), "w") as new_manifest:
        yaml.dump(manifest_dict, new_manifest, default_flow_style=False, allow_unicode=True)


@pytest.fixture(scope="function")
def project(request):
    dependencies = request.param['dependencies']

    project_path = mkdtemp(dir='.')
    try:
        copy_tree(os.path.abspath(os.path.join("integration_tests", "fixtures", "sample_project")), project_path)

        component_manager = ComponentManager(path=project_path)
        component_manager.create_manifest({})

        for library in dependencies.keys():

            try:
                include = dependencies[library].pop('include')
                include_library(project_path, include)
            except KeyError:
                pass

            add_dependency_to_manifest(project_path, dependencies, library)

        yield os.path.abspath(project_path)
    finally:
        shutil.rmtree(project_path)
