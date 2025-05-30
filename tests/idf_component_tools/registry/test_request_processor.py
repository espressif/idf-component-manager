# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import pytest

from idf_component_tools.registry.request_processor import (
    _request_cache,
    cache_request,
    cache_to_dict,
)


def test_cache_to_dict_basic():
    cache = {}

    def sample_function(a, b):
        return a + b

    # First call - should compute the result and store it in the cache
    result1 = cache_to_dict(cache, sample_function, 1, 2)
    assert result1 == 3
    assert len(cache) == 1

    # Second call with the same arguments - should retrieve result from cache
    result2 = cache_to_dict(cache, sample_function, 1, 2)
    assert result2 == 3
    assert len(cache) == 1


def test_cache_to_dict_with_dict_arg():
    cache = {}

    def sample_function(a):
        return a['value'] * 2

    arg = {'value': 5}

    # Use dict in args
    result1 = cache_to_dict(cache, sample_function, arg)
    result2 = cache_to_dict(cache, sample_function, arg)
    assert result1 == 10
    assert result2 == 10
    assert len(cache) == 1


def test_cache_to_dict_with_kwargs():
    cache = {}

    def sample_function(a, **kwargs):
        return a + kwargs['b']['value']

    # Use dict in kwargs
    result1 = cache_to_dict(cache, sample_function, 1, b={'value': 2})
    result2 = cache_to_dict(cache, sample_function, 1, b={'value': 2})
    assert result1 == 3  # Adjusted sample_function to handle dict in kwargs
    assert result2 == 3
    assert len(cache) == 1


@pytest.mark.enable_request_cache
def test_cache_request_with_caching_enabled(mocker):
    # Mock function to be decorated
    mock_func = mocker.Mock(return_value='response')
    decorated_func = cache_request(mock_func)

    # Clear the cache before testing
    _request_cache.clear()

    # Call the function with caching enabled
    result1 = decorated_func(method='GET', url='http://example.com')
    result2 = decorated_func(method='GET', url='http://example.com')

    assert result1 == 'response'
    assert result2 == 'response'
    assert mock_func.call_count == 1  # Should be called only once due to caching
    assert len(_request_cache) == 1  # Cache should have one entry


def test_cache_request_with_caching_disabled(mocker):
    # Mock function to be decorated
    mock_func = mocker.Mock(return_value='response')
    decorated_func = cache_request(mock_func)

    # Clear the cache before testing
    _request_cache.clear()

    # Call the function with caching disabled
    result1 = decorated_func(method='GET', url='http://example.com')
    result2 = decorated_func(method='GET', url='http://example.com')

    assert result1 == 'response'
    assert result2 == 'response'
    assert mock_func.call_count == 2  # Should be called twice since caching is disabled
    assert len(_request_cache) == 0  # Cache should remain empty


@pytest.mark.enable_request_cache
def test_cache_request_caches_only_get_and_head(mocker):
    # Mock function to be decorated
    mock_func = mocker.Mock(return_value='response')
    decorated_func = cache_request(mock_func)

    # Clear the cache before testing
    _request_cache.clear()

    results = [
        # Call the function with HEAD method
        decorated_func(method='GET', url='http://example.com'),
        decorated_func(method='GET', url='http://example.com'),
        # Call the function with HEAD method
        decorated_func(method='HEAD', url='http://example.com'),
        decorated_func(method='HEAD', url='http://example.com'),
        # Call the function with POST method
        decorated_func(method='POST', url='http://example.com'),
        decorated_func(method='POST', url='http://example.com'),
    ]

    assert results == ['response'] * 6
    # mock_func should be called once for GET and once for HEAD (due to caching), and twice for POST
    assert mock_func.call_count == 4
    expected_calls = [
        mocker.call(method='GET', url='http://example.com'),
        mocker.call(method='HEAD', url='http://example.com'),
        mocker.call(method='POST', url='http://example.com'),
        mocker.call(method='POST', url='http://example.com'),
    ]
    assert mock_func.call_args_list == expected_calls
    assert len(_request_cache) == 2  # Cache should have entries for GET and HEAD


@pytest.mark.enable_request_cache
def test_cache_request_with_do_not_cache(mocker):
    # Mock function to be decorated
    mock_func = mocker.Mock(return_value='response')
    decorated_func = cache_request(mock_func)

    # Clear the cache before testing
    _request_cache.clear()

    # Call the function with do_not_cache set to True
    result1 = decorated_func(method='GET', url='http://example.com', do_not_cache=True)
    result2 = decorated_func(method='GET', url='http://example.com', do_not_cache=True)

    assert result1 == 'response'
    assert result2 == 'response'
    assert mock_func.call_count == 2  # Should be called twice since caching is disabled
    assert len(_request_cache) == 0  # Cache should remain empty
