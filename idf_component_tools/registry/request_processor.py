# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t
import warnings
from copy import deepcopy
from http import HTTPStatus

import requests
from pydantic import ValidationError
from requests import Response

from idf_component_tools import ComponentManagerSettings, debug

from .api_models import ApiBaseModel, ErrorResponse
from .client_errors import (
    KNOWN_API_ERRORS,
    APIClientError,
    ContentTooLargeError,
    NetworkConnectionError,
    StorageFileNotFound,
)

DEFAULT_REQUEST_TIMEOUT = (
    10.05,  # Connect timeout
    60.1,  #  Read timeout
)

# Storage for caching requests
_request_cache: t.Dict[t.Tuple[t.Any], Response] = {}


def join_url(*args) -> str:
    """
    Joins given arguments into an url and add trailing slash
    """
    parts = [part[:-1] if part and part[-1] == '/' else part for part in args]
    return '/'.join(parts)


def make_hashable(input_object):
    """Convert input_object to a hashable object"""
    if isinstance(input_object, (tuple, list)):
        return tuple(make_hashable(e) for e in input_object)
    elif isinstance(input_object, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in input_object.items()))
    elif isinstance(input_object, set):
        return frozenset(make_hashable(e) for e in input_object)
    else:
        return input_object


def cache_to_dict(cache_dict: t.Dict[t.Any, t.Any], func: t.Callable, *args, **kwargs) -> t.Any:
    """Cache the result of a function call in a dictionary"""
    cache_key = (make_hashable(args), make_hashable(kwargs))
    if cache_key in cache_dict:
        return cache_dict[cache_key]
    result = func(*args, **kwargs)
    cache_dict[cache_key] = result
    return result


def cache_request(func):
    """Decorator to conditionally cache GET and HEAD requests based on CACHE_HTTP_REQUESTS"""

    def wrapper(*args, **kwargs):
        do_not_cache = kwargs.pop('do_not_cache', False)

        cache_conditions = [
            ComponentManagerSettings().CACHE_HTTP_REQUESTS,
            kwargs.get('method', '').lower() in ['get', 'head'],
            do_not_cache is False,
        ]

        if all(cache_conditions):
            return cache_to_dict(_request_cache, func, *args, **kwargs)
        return func(*args, **kwargs)

    return wrapper


@cache_request
def make_request(
    session: requests.Session,
    endpoint: str,
    data: t.Optional[t.Dict],
    json: t.Optional[t.Dict],
    headers: t.Optional[t.Dict],
    timeout: t.Union[float, t.Tuple[float, float]],
    method: str = 'GET',
) -> Response:
    try:
        debug(f'HTTP request: {method.upper()} {endpoint}')
        response = session.request(
            method,
            endpoint,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            verify=ComponentManagerSettings().VERIFY_SSL,
        )
    except requests.exceptions.ConnectionError as e:
        raise NetworkConnectionError(str(e), endpoint=endpoint)
    except requests.exceptions.RequestException as e:
        raise APIClientError(f'HTTP request error {e}', endpoint=endpoint)

    debug(f'HTTP response: {response.status_code} total: {response.elapsed.total_seconds()}s')
    return response


def handle_response_errors(
    response: requests.Response,
    endpoint: str,
    use_storage: bool,
) -> t.Dict:
    if response.status_code == HTTPStatus.NO_CONTENT:
        return {}
    elif 400 <= response.status_code < 500:
        if use_storage:
            if response.status_code == HTTPStatus.NOT_FOUND:
                raise StorageFileNotFound()
            raise APIClientError(
                'Error during request',
                endpoint=endpoint,
                status_code=response.status_code,
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
    if response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE:
        raise ContentTooLargeError(
            'Error during request. The provided content is too large '
            'to process. Please reduce the size and try again.',
            endpoint=response.url,
            status_code=response.status_code,
        )

    if response.status_code == HTTPStatus.FORBIDDEN:
        raise APIClientError(' '.join(response.json()['messages']) + f'\nURL: {response.url}')

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
    timeout: t.Optional[t.Union[float, t.Tuple[float, float]]] = None,
    use_storage: bool = False,
    do_not_cache=False,
) -> t.Dict:
    endpoint = join_url(url, *path)

    request_timeout: t.Optional[t.Union[float, t.Tuple[float, float]]] = (
        ComponentManagerSettings().API_TIMEOUT or timeout
    )

    if request_timeout is None:
        request_timeout = DEFAULT_REQUEST_TIMEOUT

    response = make_request(
        session,
        endpoint,
        data,
        json,
        headers,
        request_timeout,
        method=method,
        do_not_cache=do_not_cache,
    )
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
