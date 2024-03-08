# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t

from idf_component_tools.manifest import Manifest


class ComponentDetails(Manifest):
    def __init__(
        self,
        download_url: t.Optional[str] = None,  # Direct url for tarball download
        documents: t.Optional[
            t.List[t.Dict[str, str]]
        ] = None,  # List of documents of the component
        license_url: t.Optional[str] = None,  # URL for downloading license
        examples: t.Optional[t.List[t.Dict[str, str]]] = None,  # List of examples of the component
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.download_url = download_url
        self.documents = documents
        self.license_url = license_url

        if not examples:
            examples = []

        self.examples: t.List = examples


class ComponentDetailsWithStorageURL(ComponentDetails):
    def __init__(
        self,
        storage_url: t.Optional[str] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.storage_url = storage_url
