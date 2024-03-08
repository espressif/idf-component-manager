# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t

import requests


class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token: t.Optional[str]) -> None:
        self.token = token

    def __call__(self, request):
        if self.token:
            request.headers['Authorization'] = f'Bearer {self.token}'
        return request
