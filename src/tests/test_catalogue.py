from unittest.mock import Mock, patch

import requests
import pytest

from src import catalogue as api
from flaskd.app import app


@pytest.fixture(autouse=True)
def clear_cache():
    api._cache.clear()
    yield
    api._cache.clear()


def test_cached_catalogue_and_encoded_search():
    response = Mock()
    response.json.return_value = {'metas': [
        {'id': 'tt123', 'name': 'Example', 'poster': 'https://example.com/poster.jpg'},
        {'id': 'bad', 'name': 'Invalid'},
    ]}
    with patch.object(api.requests, 'get', return_value=response) as get:
        assert len(api.catalogue('movie', 'a/b & c')) == 1
        api.catalogue('movie', 'a/b & c')
        assert get.call_count == 1
        assert '/search=a%2Fb%20%26%20c.json' in get.call_args.args[0]


def test_expired_cache_refetches():
    api._cache['/catalog/movie/top.json'] = (-10000, {'metas': []})
    with patch.object(api.requests, 'get') as get:
        get.return_value.json.return_value = {'metas': []}
        api.catalogue('movie')
        get.assert_called_once()


def test_failure_keeps_torrent_search_available():
    with patch('flaskd.app.catalogue', side_effect=requests.Timeout):
        response = app.test_client().get('/')
        assert response.status_code == 200
        assert b'Catalogue unavailable' in response.data
        assert b'/torrent-search' in response.data


def test_detail_download_query_and_escaping():
    item = api.normalize({'id': 'tt123', 'name': '<Example>', 'releaseInfo': '2021',
                          'poster': 'javascript:alert(1)'})
    assert item['poster'] == ''
    with patch('flaskd.app.details', return_value=item):
        response = app.test_client().get('/title/movie/tt123')
        assert response.status_code == 200
        assert b'&lt;Example&gt; 2021' in response.data
        assert b'<Example>' not in response.data
        assert b'action="/search"' in response.data


def test_invalid_routes_do_not_fetch():
    with patch.object(api.requests, 'get') as get:
        client = app.test_client()
        assert client.get('/?type=bad').status_code == 400
        assert client.get('/title/movie/invalid').status_code == 404
        get.assert_not_called()
