"""Optional Redis (Upstash / Vercel KV) helper over REST.
Used to remember what was already posted to channels and to count users.
Works with either UPSTASH_REDIS_REST_* or KV_REST_API_* env vars."""
import os

import requests


def _conf():
    url = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ.get("KV_REST_API_URL")
    tok = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ.get("KV_REST_API_TOKEN")
    return url, tok


def available():
    url, tok = _conf()
    return bool(url and tok)


def _cmd(*args):
    url, tok = _conf()
    if not (url and tok):
        return None
    try:
        r = requests.post(url, json=[str(a) for a in args], headers={"Authorization": f"Bearer {tok}"}, timeout=8)
        return r.json().get("result")
    except Exception:
        return None


def sismember(key, member):
    return bool(_cmd("SISMEMBER", key, member))


def sadd(key, member):
    return _cmd("SADD", key, member)


def scard(key):
    try:
        return int(_cmd("SCARD", key) or 0)
    except (TypeError, ValueError):
        return 0


def smembers(key):
    return _cmd("SMEMBERS", key) or []
