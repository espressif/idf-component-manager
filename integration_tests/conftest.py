# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import typing as t
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from ruamel.yaml import YAML

from idf_component_tools.config import root_managed_components_dir
from idf_component_tools.constants import MANIFEST_FILENAME

from .integration_test_helpers import create_component, generate_from_template
from .integration_test_helpers import idf_version as system_idf_version


@pytest.fixture  # fake fixture since can't specify `indirect` for only one fixture
def result(request):
    return getattr(request, 'param')


@pytest.fixture(scope='function')
def project(request, tmpdir_factory):
    project_path = str(tmpdir_factory.mktemp('project'))
    file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'fixtures', 'templates'))
    env = Environment(loader=file_loader)
    generate_from_template(
        os.path.join(project_path, 'CMakeLists.txt'), env.get_template('CMakeLists.txt')
    )

    # create idf root dependencies
    root_dependencies = request.param.get('root_dependencies', {})
    if not os.path.isdir(root_managed_components_dir()):
        os.makedirs(root_managed_components_dir())
    with open(os.path.join(root_managed_components_dir(), MANIFEST_FILENAME), 'w') as fw:
        YAML().dump({'dependencies': root_dependencies}, fw)

    # create project components
    components = request.param.get('components', {'main': {}})
    for component in components.keys():
        create_component(project_path, component, components[component], env)
    yield os.path.abspath(project_path)


class Snapshot:
    def __init__(self, paths: t.Union[t.List[str], str]) -> None:
        self.files: t.Dict[str, t.Optional[bytes]] = {}

        if isinstance(paths, str):
            paths = [paths]

        for path in [os.path.realpath(os.path.expanduser(p)) for p in paths]:
            self.files.update(self._record(path))

    def _record(self, path, res=None):
        if res is None:
            res = {}

        if os.path.isfile(path):  # if it's an existing file, record the content
            try:
                with open(path, 'rb') as fr:
                    res.update({path: fr.read()})
            except PermissionError:
                pass
        elif os.path.isdir(path):  # if it's an existing dir, recursively record the content
            if not os.listdir(path):
                res.update({path: None})
            else:
                for item in os.listdir(path):
                    res.update(self._record(os.path.join(path, item), res))
        else:  # not exists
            res.update({path: None})

        return res

    def revert(self):
        for path, content in self.files.items():
            if content is not None:
                if not os.path.isdir(os.path.dirname(path)):
                    os.makedirs(os.path.dirname(path))
                with open(path, 'wb+') as fw:
                    fw.write(content)
            else:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.remove(path)
                else:
                    pass


@pytest.fixture(autouse=True)
def content_snapshot(request):
    snapshot_marker = request.node.get_closest_marker('snapshot')
    if not snapshot_marker:
        yield
    else:
        snapshot = Snapshot(snapshot_marker.args)
        yield
        snapshot.revert()


@pytest.fixture()
def fixtures_path():
    return Path(os.path.join(os.path.dirname(__file__), 'fixtures'))


def pytest_configure(config):
    for name, description in {
        'snapshot': 'snapshot the specified files/folders and revert the content after test case'
    }.items():
        config.addinivalue_line('markers', f'{name}: {description}')


@pytest.fixture(scope='session')
def idf_version():
    return system_idf_version()


@pytest.fixture
def debug_mode(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_DEBUG_MODE', '1')
