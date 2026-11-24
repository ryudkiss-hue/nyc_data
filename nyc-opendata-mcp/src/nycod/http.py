"""Cached HTTP GET for NYC Open Data (Socrata) and DOT ArcGIS.

Same behaviour as msb.py's _get (JSON, three tries, an ArcGIS {"error": ...} body raises), with two additions for a
long-running local server: cached files expire (msb.py's never do), and a Socrata app token, proxy and CA bundle can be
set by environment variable.

Environment:
  NYCOD_CACHE            cache folder (default ~/.cache/nycod)
  NYCOD_TTL_OPENDATA     seconds an Open Data answer stays fresh (default 21600 = 6 h)
  NYCOD_TTL_ARCGIS       seconds a DOT ArcGIS answer stays fresh (default 604800 = 7 days)
  NYC_OPENDATA_APP_TOKEN Socrata app token (optional; raises the rate limit)
  NYCOD_CA_BUNDLE        PEM file for TLS inspection on the DOT network (optional)
  HTTPS_PROXY            honoured by urllib as usual
"""
import contextlib
import contextvars
import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

CACHE = os.environ.get('NYCOD_CACHE', os.path.join(os.path.expanduser('~'), '.cache', 'nycod'))
TTL_OPENDATA = int(os.environ.get('NYCOD_TTL_OPENDATA', 6 * 3600))
TTL_ARCGIS = int(os.environ.get('NYCOD_TTL_ARCGIS', 7 * 86400))
APP_TOKEN = os.environ.get('NYC_OPENDATA_APP_TOKEN', '').strip()
CA_BUNDLE = os.environ.get('NYCOD_CA_BUNDLE', '').strip()
USER_AGENT = 'nyc-opendata-mcp/1.0 (NYC DOT SIM make-safe-batch)'


class FetchError(RuntimeError):
    """A request failed after retries. The message names the URL and the server's answer."""


def _ctx():
    if CA_BUNDLE:
        return ssl.create_default_context(cafile=CA_BUNDLE)
    return None


def _ttl(url):
    return TTL_OPENDATA if 'data.cityofnewyork.us' in url else TTL_ARCGIS


def cache_path(url):
    return os.path.join(CACHE, hashlib.md5(url.encode()).hexdigest() + '.json')


_FRESH = contextvars.ContextVar('nycod_fresh', default=False)


@contextlib.contextmanager
def bypass_cache(on=True):
    """Inside this block every get_json call skips the cache read (answers are still cached)."""
    tok = _FRESH.set(bool(on))
    try:
        yield
    finally:
        _FRESH.reset(tok)


def get_json(url, timeout=90, fresh=None):
    """GET url and parse JSON, from the cache when a fresh enough copy exists.

    fresh=True skips the cache read (the answer is still written to the cache); None follows bypass_cache()."""
    if fresh is None:
        fresh = _FRESH.get()
    os.makedirs(CACHE, exist_ok=True)
    p = cache_path(url)
    if not fresh and os.path.exists(p) and time.time() - os.path.getmtime(p) < _ttl(url):
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json'}
    if APP_TOKEN and 'data.cityofnewyork.us' in url:
        headers['X-App-Token'] = APP_TOKEN
    err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
                d = json.load(r)
            if isinstance(d, dict) and 'error' in d:
                raise FetchError(f"server error for {url}: {d['error']}")
            tmp = p + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(d, f)
            os.replace(tmp, p)
            return d
        except urllib.error.HTTPError as e:
            body = e.read()[:600].decode('utf-8', 'replace')
            err = FetchError(f'HTTP {e.code} for {url}: {body}')
            if 400 <= e.code < 500 and e.code != 429:
                break   # a bad query will not get better on retry
        except FetchError as e:
            err = e
            break
        except Exception as e:   # timeouts, resets, DNS
            err = FetchError(f'{type(e).__name__} for {url}: {e}')
        time.sleep(2 * (attempt + 1))
    raise err


def clear_cache():
    """Delete every cached answer. Returns how many files were removed."""
    if not os.path.isdir(CACHE):
        return 0
    n = 0
    for name in os.listdir(CACHE):
        if name.endswith('.json'):
            os.remove(os.path.join(CACHE, name))
            n += 1
    return n


def urlencode(params):
    return urllib.parse.urlencode(params)
