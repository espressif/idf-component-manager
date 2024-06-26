# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import subprocess
import typing as t

import yaml
from jinja2 import Environment, Template

from idf_component_manager.core import ComponentManager


def generate_from_template(
    file_path: str, template: Template, **kwargs: t.Union[str, t.List[str]]
) -> None:
    """
    Generates file according to the template with given arguments
    """
    with open(file_path, 'w') as cmake_lists:
        target_cmake_lists = template.render(**kwargs)
        cmake_lists.write(target_cmake_lists)


def get_component_path(project_path: str, component_name: str) -> str:
    """
    Assemblies component path,
    if the component is `main` it is not placed in the `components` folder
    """
    return os.path.join(
        project_path, 'components' if component_name != 'main' else '', component_name
    )


def create_manifest(
    project_path: str, component_dict: t.Dict, libraries: list, component_name: str
) -> None:
    """
    If the component contains some dependencies
    creates idf_component.yml file for the component and
    updates its value according to the test scenario
    """
    if len(libraries) == 0 or 'dependencies' not in component_dict.keys():
        return
    component_manager = ComponentManager(path=project_path)
    component_manager.create_manifest(component_name)
    component_path = get_component_path(project_path, component_name)

    with open(os.path.join(component_path, 'idf_component.yml')) as manifest:
        manifest_dict = yaml.safe_load(manifest)
    for library in libraries:
        manifest_dict['dependencies'][library] = component_dict['dependencies'][library]
        if 'targets' in component_dict:
            manifest_dict['targets'] = component_dict['targets']
        if 'version' in component_dict:
            manifest_dict['version'] = component_dict['version']

    with open(os.path.join(component_path, 'idf_component.yml'), 'w') as new_manifest:
        yaml.dump(manifest_dict, new_manifest, default_flow_style=False, allow_unicode=True)


def create_component(
    project_path: str,
    component_name: str,
    component_dict: t.Dict,
    env: Environment,
    function_name: str = 'app_main',
) -> None:
    """
    Procedure creates the component in the project that contains
    source and header files (with same name as component), and CMakeLists.txt.
    The default name of the function in every source and header file is `app_main`.
    """

    component_path = get_component_path(project_path, component_name)
    os.makedirs(os.path.join(component_path, 'include'))

    include_list, libraries_for_manifest = get_dependencies(component_dict)
    create_manifest(project_path, component_dict, libraries_for_manifest, component_name)

    generate_from_template(
        os.path.join(component_path, f'{component_name}.c'),
        env.get_template(os.path.join('src', 'sample_src.c')),
        header_files=[f'{component_name}.h'] + include_list,
        func_name=function_name,
    )

    generate_from_template(
        os.path.join(component_path, 'include', f'{component_name}.h'),
        env.get_template(os.path.join('include', 'sample_header.h')),
        func_name=function_name,
    )

    component_register_parameters = []
    if 'cmake_lists' in component_dict.keys():
        component_register_parameters = [
            f'{key.upper()} {value}' for key, value in component_dict['cmake_lists'].items()
        ]

    generate_from_template(
        os.path.join(component_path, 'CMakeLists.txt'),
        env.get_template(os.path.join('src', 'CMakeLists.txt')),
        parameters=component_register_parameters,
        component=component_name,
    )


def get_dependencies(component_dict: t.Dict) -> t.Tuple:
    """
    Returns tuple of two lists - dependencies for including in the source file
    and dependencies for adding to manifest
    """
    if 'dependencies' not in component_dict.keys():
        return [], []
    dependencies = component_dict['dependencies']
    include_list = [
        dependencies[library].pop('include', None)
        for library in dependencies.keys()
        if dependencies[library].get('include', None)
    ]
    libraries_for_manifest = [
        library
        for library in dependencies.keys()
        if 'git' in dependencies[library].keys()
        or 'version' in dependencies[library].keys()
        or 'path' in dependencies[library].keys()
        or 'override_path' in dependencies[library].keys()
    ]

    return include_list, libraries_for_manifest


def fixtures_path(*args):
    return os.path.join(os.path.dirname(__file__), '..', 'tests', 'fixtures', *args)


def live_print_call(*args, **kwargs):
    default_kwargs = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
    }
    kwargs.update(default_kwargs)
    process = subprocess.Popen(*args, **kwargs)

    try:
        string_type = basestring  # type: ignore
    except NameError:
        string_type = str

    res = ''
    for line in process.stdout:
        if not isinstance(line, string_type):
            line = line.decode('utf-8')
        line = line.rstrip()
        logging.info(line)
        res += ' ' + line.strip()
    return res


def idf_version():
    return live_print_call(['idf.py', '--version'])


def project_action(project_path, *actions):
    return live_print_call(['idf.py', '-C', str(project_path)] + list(actions))


def assert_dependency_version(project_path, component_name, version):
    with open(os.path.join(project_path, 'dependencies.lock')) as f:
        lock = yaml.safe_load(f)
        assert component_name in lock['dependencies']
        assert lock['dependencies'][component_name]['version'] == version


def set_target(project_path, target):
    return live_print_call(['idf.py', '-C', project_path, 'set-target', target])


def current_idf_in_the_list(*versions):
    """Returns True if current IDF version is in the list of versions"""
    current_version = idf_version()
    for version in versions:
        if version in current_version:
            return True

    return False
