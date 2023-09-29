# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import shutil

import pytest
from jinja2 import Environment, FileSystemLoader

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

    components = request.param.get('components', {'main': {}})
    for component in components.keys():
        create_component(project_path, component, components[component], env)
    yield os.path.abspath(project_path)


class Snapshot:
    def __init__(self, paths):  # type: (list[str] | str) -> None
        self.files = {}  # type: dict[str, bytes | None]

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


def pytest_configure(config):
    for name, description in {
        'snapshot': 'snapshot the specified files/folders and revert the content after test case'
    }.items():
        config.addinivalue_line('markers', '{}: {}'.format(name, description))


@pytest.fixture(scope='session')
def idf_version():
    return system_idf_version()
