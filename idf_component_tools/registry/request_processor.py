# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import typing as t
import warnings
from copy import deepcopy

import requests
from pydantic import ValidationError
from requests import Response

from idf_component_tools.environment import getenv_bool_or_string

from .api_models import ApiBaseModel, ErrorResponse
from .client_errors import (
    KNOWN_API_ERRORS,
    APIClientError,
    ContentTooLargeError,
    NetworkConnectionError,
    StorageFileNotFound,
)

DEFAULT_TIMEOUT = (6.05, 30.1)  # Connect timeout  # Read timeout


def join_url(*args) -> str:
    """
    Joins given arguments into an url and add trailing slash
    """
    parts = [part[:-1] if part and part[-1] == '/' else part for part in args]
    return '/'.join(parts)


def get_timeout() -> t.Union[float, t.Tuple[float, float]]:
    try:
        return float(os.environ['IDF_COMPONENT_SERVICE_TIMEOUT'])
    except ValueError:
        raise APIClientError(
            'Cannot parse IDF_COMPONENT_SERVICE_TIMEOUT. It should be a number in seconds.'
        )
    except KeyError:
        return DEFAULT_TIMEOUT


def verify_ssl() -> t.Union[bool, str]:
    """Returns either True, False or a path to a CA bundle file"""

    return getenv_bool_or_string('IDF_COMPONENT_VERIFY_SSL', True)


def make_request(
    method: str,
    session: requests.Session,
    endpoint: str,
    data: t.Optional[t.Dict],
    json: t.Optional[t.Dict],
    headers: t.Optional[t.Dict],
    timeout: t.Union[float, t.Tuple[float, float]],
) -> Response:
    try:
        response = session.request(
            method,
            endpoint,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            verify=verify_ssl(),
        )
    except requests.exceptions.ConnectionError as e:
        raise NetworkConnectionError(str(e), endpoint=endpoint)
    except requests.exceptions.RequestException:
        raise APIClientError('HTTP request error', endpoint=endpoint)

    return response


def handle_response_errors(
    response: requests.Response,
    endpoint: str,
    use_storage: bool,
) -> t.Dict:
    if response.status_code == 204:  # NO CONTENT
        return {}
    elif 400 <= response.status_code < 500:
        if use_storage:
            if response.status_code == 404:
                raise StorageFileNotFound()
            raise APIClientError(
                'Error during request', endpoint=endpoint, status_code=response.status_code
            )
        handle_4xx_error(response)
    elif 500 <= response.status_code < 600:
        raise APIClientError(
            'Internal server error happened while processing request.',
            endpoint=endpoint,
            status_code=response.status_code,
        )

    return response.json()


def handle_4xx_error(response: requests.Response) -> None:
    if response.status_code == 413:
        raise ContentTooLargeError(
            'Error during request. The provided content is too large '
            'to process. Please reduce the size and try again.',
            endpoint=response.url,
            status_code=response.status_code,
        )

    try:
        error = ErrorResponse.model_validate(response.json())
        name = error.error
        messages = error.messages
    except ValidationError as e:
        raise APIClientError(
            f'API Endpoint returned unexpected error description:\n{e}',
            endpoint=response.url,
            status_code=response.status_code,
        )
    except ValueError:
        raise APIClientError(
            'Server returned an error in unexpected format',
            endpoint=response.url,
            status_code=response.status_code,
        )

    exception = KNOWN_API_ERRORS.get(name, APIClientError)
    if isinstance(messages, list):
        raise exception('\n'.join(messages))
    else:
        raise exception(
            'Error during request:\n{}\nStatus code: {} Error code: {}'.format(
                str(messages), response.status_code, name
            )
        )


def base_request(
    url: str,
    session: requests.Session,
    method: str,
    path: t.List[str],
    data: t.Optional[t.Dict] = None,
    json: t.Optional[t.Dict] = None,
    headers: t.Optional[t.Dict] = None,
    schema: t.Optional[ApiBaseModel] = None,
    use_storage: bool = False,
) -> t.Dict:
    endpoint = join_url(url, *path)
    timeout = get_timeout()
    response = make_request(method, session, endpoint, data, json, headers, timeout)
    response_json = handle_response_errors(response, endpoint, use_storage)

    if schema is None:
        return response_json

    try:
        # model validation will modify the response_json, so we need to deepcopy it
        # besides, the unknown fields will be ignored, suppressing the warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            schema.model_validate(deepcopy(response_json))
    except ValidationError as e:
        raise APIClientError(
            f'API Endpoint returned unexpected JSON:\n{e}',
            endpoint=endpoint,
        )
    except (ValueError, KeyError, IndexError):
        raise APIClientError('Unexpected component server response', endpoint=endpoint)

    return response_json
