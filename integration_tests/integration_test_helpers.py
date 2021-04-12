import os

import yaml
from jinja2 import Environment, Template

from idf_component_manager.core import ComponentManager

try:
    from typing import Any  # noqa
except ImportError:
    pass


def generate_from_template(file_path, template, **kwargs):
    # type: (str, Template, Any[str]) -> None
    """
    Generates file according to the template with given arguments
    """
    with open(file_path, 'w') as cmake_lists:
        target_cmake_lists = template.render(**kwargs)
        cmake_lists.write(target_cmake_lists)


def get_component_path(project_path, component_name):
    # type: (str, str) -> str
    """
    Assemblies component path, if the component is `main` it is not placed in the `components` folder
    """
    return os.path.join(project_path, 'components' if component_name != 'main' else '', component_name)


def create_manifest(project_path, component_dict, libraries, component_name):
    # type: (str, dict, list, str) -> None
    """
    If the component contains some dependencies
    creates idf_component.yml file for the component and updates its value according to the test scenario
    """
    if len(libraries) == 0 or 'dependencies' not in component_dict.keys():
        return
    component_manager = ComponentManager(path=project_path)
    component_manager.create_manifest({'component': component_name})
    component_path = get_component_path(project_path, component_name)

    with open(os.path.join(component_path, 'idf_component.yml')) as manifest:
        manifest_dict = yaml.safe_load(manifest)
    for library in libraries:
        manifest_dict['dependencies'][library] = component_dict['dependencies'][library]

    with open(os.path.join(component_path, 'idf_component.yml'), 'w') as new_manifest:
        yaml.dump(manifest_dict, new_manifest, default_flow_style=False, allow_unicode=True)


def create_component(project_path, component_name, component_dict, env, function_name='app_main'):
    # type: (str, str, dict, Environment, str) -> None
    """
    Procedure creates the component in the project that contains source and header files (with same name as component),
    and CMakeLists.txt. The default name of the function in every source and header file is `app_main`.
    """

    component_path = get_component_path(project_path, component_name)
    os.makedirs(os.path.join(component_path, 'include'))

    include_list, libraries_for_manifest = get_dependencies(component_dict)
    create_manifest(project_path, component_dict, libraries_for_manifest, component_name)

    generate_from_template(
        os.path.join(component_path, '{}.c'.format(component_name)),
        env.get_template(os.path.join('src', 'sample_src.c')),
        header_files=['{}.h'.format(component_name)] + include_list,
        func_name=function_name)

    generate_from_template(
        os.path.join(component_path, 'include', '{}.h'.format(component_name)),
        env.get_template(os.path.join('include', 'sample_header.h')),
        func_name=function_name)

    component_register_parameters = []
    if 'cmake_lists' in component_dict.keys():
        component_register_parameters = [
            '{} {}'.format(key.upper(), value) for key, value in component_dict['cmake_lists'].items()
        ]

    generate_from_template(
        os.path.join(component_path, 'CMakeLists.txt'),
        env.get_template(os.path.join('src', 'CMakeLists.txt')),
        parameters=component_register_parameters,
        component=component_name)


def get_dependencies(component_dict):
    # type: (dict) -> tuple
    """
    Returns tuple of two lists - dependencies for including in the source file and dependencies for adding to manifest
    """
    if 'dependencies' not in component_dict.keys():
        return [], []
    dependencies = component_dict['dependencies']
    include_list = [
        dependencies[library].pop('include', None) for library in dependencies.keys()
        if dependencies[library].get('include', None)
    ]
    libraries_for_manifest = [
        library for library in dependencies.keys()
        if 'git' in dependencies[library].keys() or 'version' in dependencies[library].keys()
    ]

    return include_list, libraries_for_manifest
