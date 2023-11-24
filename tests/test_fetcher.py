# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os.path
from io import open

import pytest

from idf_component_tools.errors import ComponentModifiedError, InvalidComponentHashError
from idf_component_tools.hash_tools.constants import HASH_FILENAME
from idf_component_tools.manifest import ComponentVersion
from idf_component_tools.manifest.solved_component import SolvedComponent
from idf_component_tools.sources import WebServiceSource
from idf_component_tools.sources.fetcher import ComponentFetcher


def test_fetcher_download_and_create_hash(fixtures_path):
    components_folder_path = os.path.join(fixtures_path, 'components')
    source = WebServiceSource({'service_url': 'https://repo.example.com'})
    component = SolvedComponent(
        'cmp',
        ComponentVersion('1.0.0'),
        source,
        component_hash='0d7b0d0e9ab239cf4e127dd08990caf869158324c251dc1fbacacbe788dc3f35',
    )
    fetcher = ComponentFetcher(component, components_folder_path)
    component_path = os.path.join(components_folder_path, 'cmp')

    try:
        fetcher.create_hash(component_path, component.component_hash)

        with pytest.raises(
            ComponentModifiedError,
            match='Component directory was modified ' 'on the disk since the last run of the CMake',
        ):
            fetcher.download()

        hash_file = os.path.join(component_path, HASH_FILENAME)
        with open(hash_file, mode='w+', encoding='utf-8') as f:
            f.write(u'Wrong hash')

        with pytest.raises(InvalidComponentHashError, match='File .component_hash for component *'):
            fetcher.download()

    finally:
        os.remove(os.path.join(component_path, HASH_FILENAME))
