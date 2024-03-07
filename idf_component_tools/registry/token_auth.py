# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from typing import Optional

import requests


class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token: Optional[str]) -> None:
        self.token = token

    def __call__(self, request):
        if self.token:
            request.headers['Authorization'] = f'Bearer {self.token}'
        return request
