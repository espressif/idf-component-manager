# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os

import pytest
from jinja2 import Environment, FileSystemLoader

from .integration_test_helpers import create_component, generate_from_template


@pytest.fixture  # fake fixture since can't specify `indirect` for only one fixture
def result(request):
    return getattr(request, 'param')


@pytest.fixture(scope='function')
def project(request, tmpdir_factory):
    project_path = str(tmpdir_factory.mktemp('project'))
    file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'fixtures', 'templates'))
    env = Environment(loader=file_loader)
    generate_from_template(os.path.join(project_path, 'CMakeLists.txt'), env.get_template('CMakeLists.txt'))

    components = request.param.get('components', {'main': {}})
    for component in components.keys():
        create_component(project_path, component, components[component], env)
    yield os.path.abspath(project_path)
