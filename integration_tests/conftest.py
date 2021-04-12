import os
import shutil
from tempfile import mkdtemp

import pytest
from jinja2 import Environment, FileSystemLoader

from .integration_test_helpers import create_component, generate_from_template


@pytest.fixture(scope='function')
def project(request):
    project_path = mkdtemp(dir='.')
    file_loader = FileSystemLoader(os.path.join('integration_tests', 'fixtures', 'templates'))
    env = Environment(loader=file_loader)
    generate_from_template(os.path.join(project_path, 'CMakeLists.txt'), env.get_template('CMakeLists.txt'))

    try:
        components = request.param['components']
        for component in components.keys():
            create_component(project_path, component, components[component], env)
        yield os.path.abspath(project_path)
    finally:
        shutil.rmtree(project_path)
