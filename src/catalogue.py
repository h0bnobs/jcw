"""Small, bounded cache for Cinemeta's public metadata API."""
from collections import OrderedDict
from threading import Lock
from time import monotonic
from urllib.parse import quote, urlsplit
import re

import requests

BASE_URL = 'https://v3-cinemeta.strem.io'
_cache = OrderedDict()
_lock = Lock()


def fetch(path):
    with _lock:
        entry = _cache.get(path)
        if entry and monotonic() - entry[0] < 900:
            _cache.move_to_end(path)
            return entry[1]
    response = requests.get(BASE_URL + path, timeout=(3, 8))
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError('Invalid catalogue response')
    with _lock:
        _cache[path] = (monotonic(), data)
        _cache.move_to_end(path)
        while len(_cache) > 128:
            _cache.popitem(last=False)
    return data


def normalize(item):
    if not isinstance(item, dict) or not re.fullmatch(r'tt\d+', str(item.get('id', ''))):
        return None
    if not isinstance(item.get('name'), str) or not item['name'].strip():
        return None
    poster = item.get('poster', '')
    if not isinstance(poster, str) or urlsplit(poster).scheme != 'https':
        poster = ''
    return {
        'id': item['id'], 'name': item['name'], 'poster': poster,
        'year': str(item.get('releaseInfo') or item.get('year') or ''),
        'description': str(item.get('description') or ''),
        'runtime': str(item.get('runtime') or ''),
    }


def catalogue(kind, query=''):
    if kind not in ('movie', 'series'):
        raise ValueError('Invalid media type')
    extra = '/search=' + quote(query, safe='') if query else ''
    data = fetch(f'/catalog/{kind}/top{extra}.json')
    items = data.get('metas')
    if not isinstance(items, list):
        raise ValueError('Invalid catalogue response')
    return [value for item in items[:100] if (value := normalize(item))][:60]


def details(kind, identifier):
    if kind not in ('movie', 'series') or not re.fullmatch(r'tt\d+', identifier):
        raise ValueError('Invalid title')
    return normalize(fetch(f'/meta/{kind}/{identifier}.json').get('meta'))
