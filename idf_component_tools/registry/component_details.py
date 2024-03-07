# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from typing import Dict, List, Optional

from idf_component_tools.manifest import Manifest


class ComponentDetails(Manifest):
    def __init__(
        self,
        download_url: Optional[str] = None,  # Direct url for tarball download
        documents: Optional[List[Dict[str, str]]] = None,  # List of documents of the component
        license_url: Optional[str] = None,  # URL for downloading license
        examples: Optional[List[Dict[str, str]]] = None,  # List of examples of the component
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.download_url = download_url
        self.documents = documents
        self.license_url = license_url

        if not examples:
            examples = []

        self.examples: List = examples


class ComponentDetailsWithStorageURL(ComponentDetails):
    def __init__(
        self,
        storage_url: Optional[str] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.storage_url = storage_url
