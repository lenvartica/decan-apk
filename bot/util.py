"""Small shared helpers."""
import html
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; DecanBot/2.0; +https://www.decankonnect.co.ke)"}


def esc(s):
    return html.escape(str(s or ""))


def human(n):
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def truncate(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def strip_html(s):
    s = re.sub(r"<(script|style).*?</\1>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return " ".join(html.unescape(s).split())


def get_json(url, **kw):
    r = requests.get(url, timeout=15, headers=kw.pop("headers", UA), **kw)
    r.raise_for_status()
    return r.json()


def get_text(url, timeout=12):
    r = requests.get(url, timeout=timeout, headers=UA)
    r.raise_for_status()
    return r.text


def download_bytes(url, limit, headers=None):
    """Download a file into memory, refusing anything bigger than `limit` bytes."""
    h = dict(UA)
    h.update(headers or {})
    buf = bytearray()
    with requests.get(url, stream=True, timeout=30, headers=h) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        if total and total > limit:
            raise ValueError("file too large")
        for chunk in r.iter_content(256 * 1024):
            buf.extend(chunk)
            if len(buf) > limit:
                raise ValueError("file too large")
    return bytes(buf)


def fmt_num(n):
    """1234 -> 1.2K, 3400000 -> 3.4M"""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= div:
            return f"{n / div:.1f}".rstrip("0").rstrip(".") + suf
    return str(int(n))


def fmt_dur(sec):
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return "live/—"
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def ytdlp_opts(**extra):
    """Shared yt-dlp options. Optional YTDLP_COOKIES env (Netscape cookie text) helps with login/bot walls."""
    import os

    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True,
            "cachedir": False, "socket_timeout": 15}
    cookies = os.environ.get("YTDLP_COOKIES", "").strip()
    if cookies:
        path = "/tmp/decan_cookies.txt"
        with open(path, "w") as fh:
            fh.write(cookies.replace("\\n", "\n"))
        opts["cookiefile"] = path
    opts.update(extra)
    return opts
