# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_manager.utils import (
    ComponentSource,
)


class TestComponentSource:
    def test_component_source_order(self):
        assert (
            ComponentSource.IDF_COMPONENTS
            < ComponentSource.PROJECT_MANAGED_COMPONENTS
            < ComponentSource.PROJECT_EXTRA_COMPONENTS
            < ComponentSource.PROJECT_COMPONENTS
        )
        assert (
            ComponentSource.PROJECT_COMPONENTS
            > ComponentSource.PROJECT_EXTRA_COMPONENTS
            > ComponentSource.PROJECT_MANAGED_COMPONENTS
            > ComponentSource.IDF_COMPONENTS
        )

    def test_component_source_equality(self):
        assert (
            ComponentSource.IDF_COMPONENTS
            != ComponentSource.PROJECT_MANAGED_COMPONENTS
            != ComponentSource.PROJECT_COMPONENTS
            != ComponentSource.PROJECT_EXTRA_COMPONENTS
        )

        assert ComponentSource.IDF_COMPONENTS == ComponentSource('"idf_components"')
        assert ComponentSource.PROJECT_MANAGED_COMPONENTS == ComponentSource(
            '"project_managed_components"'
        )
        assert ComponentSource.PROJECT_COMPONENTS == ComponentSource('"project_components"')
        assert ComponentSource.PROJECT_EXTRA_COMPONENTS == ComponentSource(
            '"project_extra_components"'
        )

    def test_component_source_equality_str(self):
        assert ComponentSource.IDF_COMPONENTS == '"idf_components"'
        assert ComponentSource.PROJECT_MANAGED_COMPONENTS == '"project_managed_components"'
        assert ComponentSource.PROJECT_COMPONENTS == '"project_components"'
        assert ComponentSource.PROJECT_EXTRA_COMPONENTS == '"project_extra_components"'
