# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from idf_component_tools.manifest import Manifest


class ComponentDetails(Manifest):
    def __init__(
        self,
        download_url=None,  # type: str | None # Direct url for tarball download
        documents=None,  # type: list[dict[str, str]] | None # List of documents of the component
        license_url=None,  # type:str | None # URL for downloading license
        examples=None,  # type: list[dict[str, str]] | None # List of examples of the component
        *args,
        **kwargs
    ):
        super(ComponentDetails, self).__init__(*args, **kwargs)
        self.download_url = download_url
        self.documents = documents
        self.license_url = license_url

        if not examples:
            examples = []

        self.examples = examples  # type: list


class ComponentDetailsWithStorageURL(ComponentDetails):
    def __init__(
        self,
        storage_url=None,  # type: str | None
        *args,
        **kwargs
    ):
        super(ComponentDetailsWithStorageURL, self).__init__(*args, **kwargs)
        self.storage_url = storage_url
