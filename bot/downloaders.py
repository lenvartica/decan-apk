"""APK, music, movie and social-video downloaders."""
import os
import re
from urllib.parse import quote, urlparse

import requests

from . import tg
from .ui import HOME, btn, kb
from .util import download_bytes, esc, fmt_num, get_json, human, strip_html, truncate, ytdlp_opts

BRAND = "Decan Bot"
MAX_UPLOAD = 48 * 1024 * 1024  # Telegram bots can upload up to 50 MB
APTOIDE = "https://ws75.aptoide.com/api/7"


def _safe_name(s, ext):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")[:80] + ext


# ═════════════════════════ APK STORE ═════════════════════════
def apk_search(chat_id, query):
    tg.action(chat_id, "typing")
    try:
        data = get_json(f"{APTOIDE}/apps/search", params={"query": query, "limit": 8})
        apps = (data.get("datalist") or {}).get("list") or []
    except Exception:
        apps = []
    apps = [a for a in apps if a.get("package") and len(a["package"]) <= 56]
    if not apps:
        return tg.send(chat_id, f"😕 No apps found for <b>{esc(query)}</b>. Try another name.",
                       kb([[btn("🔍 Search again", "go:apk")], HOME]))
    lines, rows = [f"🔎 Results for <b>{esc(query)}</b>:\n"], []
    for i, a in enumerate(apps, 1):
        f = a.get("file") or {}
        size = human(f.get("filesize") or a.get("size"))
        rating = ((a.get("stats") or {}).get("rating") or {}).get("avg")
        stars = f" ⭐{rating:.1f}" if isinstance(rating, (int, float)) and rating else ""
        lines.append(f"{i}. <b>{esc(a.get('name'))}</b> — v{esc(f.get('vername'))} • {size}{stars}")
        rows.append([btn(f"{i}. {a.get('name', '')[:32]} ({size})", f"dl:{a['package']}")])
    rows.append([btn("🔍 Search again", "go:apk"), btn("🏠 Home", "nav:home")])
    lines.append("\nTap an app to download its APK 👇")
    tg.send(chat_id, "\n".join(lines), kb(rows))


def apk_send(chat_id, package):
    tg.action(chat_id, "typing")
    try:
        d = get_json(f"{APTOIDE}/app/getMeta", params={"package_name": package})["data"]
        f = d["file"]
        url = f["path"]
    except Exception:
        return tg.send(chat_id, "⚠️ Couldn't fetch that app right now. Try another.", kb([HOME]))
    name, ver = d.get("name") or package, f.get("vername") or ""
    size = f.get("filesize") or d.get("size") or 0
    rating = ((d.get("stats") or {}).get("rating") or {}).get("avg")
    downloads = (d.get("stats") or {}).get("downloads")
    caption = (
        f"📦 <b>{esc(name)}</b>\n🆚 Version: {esc(ver)}\n🧾 Package: <code>{esc(package)}</code>\n"
        f"💾 Size: {human(size)}\n"
        + (f"⭐ Rating: {rating:.1f}\n" if isinstance(rating, (int, float)) and rating else "")
        + (f"⬇️ Downloads: {int(downloads):,}\n" if downloads else "")
        + f"\n🤖 via {BRAND}"
    )
    after = kb([[btn("🔍 Another app", "go:apk"), btn("🏠 Home", "nav:home")]])
    if size and size <= MAX_UPLOAD:
        status = tg.send(chat_id, f"⏳ Downloading <b>{esc(name)}</b> ({human(size)})…")
        try:
            blob = download_bytes(url, MAX_UPLOAD)
            res = tg.send_document(chat_id, _safe_name(f"{name}_{ver}", ".apk"), blob, caption, after)
            mid = (status.get("result") or {}).get("message_id")
            if mid:
                tg.delete(chat_id, mid)
            if res.get("ok"):
                return
        except Exception:
            pass
    tg.send(chat_id, caption + "\n\n⚠️ Too big to send here — use the button:",
            kb([[btn(f"⬇️ Download ({human(size)})", url=url)], HOME]))


# ═════════════════════════ MOVIES (Internet Archive only) ═════════════════════════
def _stats(ident):
    """views (downloads), favorites, rating — Internet Archive has no 'likes', it has favorites & reviews."""
    for fields in (["downloads", "avg_rating", "num_reviews", "num_favorites"],
                   ["downloads", "avg_rating", "num_reviews"]):
        try:
            d = get_json("https://archive.org/advancedsearch.php", params={
                "q": f"identifier:{ident}", "fl[]": fields, "rows": 1, "output": "json"})
            docs = d["response"]["docs"]
            if docs:
                return docs[0]
        except Exception:
            continue
    return {}


def movie_search(chat_id, query):
    tg.action(chat_id, "typing")
    q = re.sub(r"[^\w\s-]", " ", query).strip()
    try:
        d = get_json("https://archive.org/advancedsearch.php", params={
            "q": f"title:({q}) AND mediatype:movies AND (collection:feature_films OR collection:moviesandfilms)",
            "fl[]": ["identifier", "title", "year", "downloads", "avg_rating"],
            "rows": 8, "output": "json", "sort[]": "downloads desc"})
        docs = d["response"]["docs"]
    except Exception:
        docs = []
    docs = [x for x in docs if len(x.get("identifier", "")) <= 56]
    if not docs:
        return tg.send(chat_id, f"😕 No movies found for <b>{esc(query)}</b> on the Internet Archive.",
                       kb([[btn("🔍 Search again", "go:movie")], HOME]))
    lines, rows = [f"🎬 Internet Archive results for <b>{esc(query)}</b>:\n"], []
    for i, m in enumerate(docs, 1):
        title = m.get("title") if isinstance(m.get("title"), str) else str(m.get("title"))
        yr = f" ({m['year']})" if m.get("year") else ""
        rate = f" • ⭐ {float(m['avg_rating']):.1f}" if m.get("avg_rating") else ""
        lines.append(f"{i}. <b>{esc(truncate(title, 70))}</b>{yr}\n    👁 {fmt_num(m.get('downloads'))} views{rate}")
        rows.append([btn(truncate(f"🎬 {title}{yr}", 52), f"mv:{m['identifier']}")])
    rows.append([btn("🔍 Search again", "go:movie"), btn("🏠 Home", "nav:home")])
    lines.append("\nTap a movie for poster, stats & links 👇")
    tg.send(chat_id, "\n".join(lines), kb(rows))


def movie_send(chat_id, ident):
    tg.action(chat_id, "typing")
    try:
        meta = get_json(f"https://archive.org/metadata/{quote(ident)}")
        md, files = meta.get("metadata", {}), meta.get("files", [])
    except Exception:
        return tg.send(chat_id, "⚠️ Couldn't load that movie.", kb([HOME]))
    st = _stats(ident)
    title = md.get("title") if isinstance(md.get("title"), str) else ident
    desc = md.get("description")
    desc = " ".join(desc) if isinstance(desc, list) else (desc or "")
    mp4s = [f for f in files if f.get("name", "").lower().endswith(".mp4")]
    pick = next((f for f in mp4s if "264" in f.get("format", "")), mp4s[0] if mp4s else None)
    details = f"https://archive.org/details/{quote(ident)}"
    rows = [[btn("▶️ Watch online", url=details)]]
    if pick:
        dl_url = f"https://archive.org/download/{quote(ident)}/{quote(pick['name'])}"
        rows.append([btn(f"⬇️ Download MP4 ({human(pick.get('size'))})", url=dl_url)])
    rows.append([btn("🔍 More movies", "go:movie"), btn("🏠 Home", "nav:home")])

    reviews = meta.get("reviews") or []
    n_rev = st.get("num_reviews") or len(reviews)
    avg = st.get("avg_rating") or (sum(float(r.get("stars", 0)) for r in reviews) / len(reviews) if reviews else None)
    year = md.get("year") or str(md.get("date", ""))[:4]
    stats = [f"👁 Views: <b>{fmt_num(st.get('downloads'))}</b>"]
    if st.get("num_favorites") is not None:
        stats.append(f"❤️ Favorites: <b>{fmt_num(st.get('num_favorites'))}</b>")
    if avg:
        stats.append(f"⭐ <b>{float(avg):.1f}</b> ({fmt_num(n_rev)} reviews)")
    caption = (
        f"🎬 <b>{esc(truncate(title, 120))}</b>" + (f" ({esc(year)})" if year else "") + "\n"
        + "   ".join(stats) + "\n"
        + (f"⏱ {esc(md.get('runtime'))}\n" if md.get("runtime") else "")
        + (f"💾 MP4: {human(pick.get('size'))}\n" if pick else "")
        + f"\n{esc(truncate(strip_html(desc), 420))}\n\n📜 Freely available via the Internet Archive."
    )
    poster = f"https://archive.org/services/img/{quote(ident)}"
    if not tg.send_photo(chat_id, poster, caption[:1000], kb(rows)).get("ok"):
        tg.send(chat_id, caption, kb(rows))


# ═════════════════════════ SOCIAL VIDEO ═════════════════════════
PLATFORMS = {
    "instagram.com": ("Instagram", "📸"), "facebook.com": ("Facebook", "📘"), "fb.watch": ("Facebook", "📘"),
    "fb.com": ("Facebook", "📘"), "tiktok.com": ("TikTok", "🎵"), "twitter.com": ("X / Twitter", "🐦"),
    "x.com": ("X / Twitter", "🐦"),
}
URL_RE = re.compile(r"https?://[^\s<>\"']+")


def platform_of(url):
    host = (urlparse(url).netloc or "").lower().split(":")[0]
    for dom, info in PLATFORMS.items():
        if host == dom or host.endswith("." + dom):
            return info
    return None


def _extract(url):
    import yt_dlp  # imported lazily — only needed for social links

    with yt_dlp.YoutubeDL(ytdlp_opts(format="best[ext=mp4]/best")) as ydl:
        info = ydl.extract_info(url, download=False)
    if info and info.get("entries"):
        info = next(iter(info["entries"]))
    return info


def social(chat_id, text):
    m = URL_RE.search(text or "")
    if not m:
        return tg.send(chat_id, "Please paste a full link (starting with https://).", kb([HOME]))
    url = m.group(0)
    plat = platform_of(url)
    if not plat:
        return tg.send(chat_id, "😕 I can download from Instagram, Facebook, TikTok and X links.", kb([HOME]))
    name, icon = plat
    status = tg.send(chat_id, f"⏳ Fetching your {icon} <b>{name}</b> video…")
    status_id = (status.get("result") or {}).get("message_id")

    def _clear():
        if status_id:
            tg.delete(chat_id, status_id)

    try:
        info = _extract(url)
        direct = info.get("url")
        if not direct:
            fmts = [f for f in info.get("formats", [])
                    if f.get("url") and f.get("vcodec") != "none" and f.get("acodec") != "none"
                    and str(f.get("protocol", "")).startswith("http")]
            direct = fmts[-1]["url"] if fmts else None
        if not direct:
            raise ValueError("no direct video url")
    except Exception:
        _clear()
        return tg.send(
            chat_id,
            f"⚠️ Couldn't get that {name} video.\n\n• Make sure the post is <b>public</b> and has a video\n"
            "• Instagram sometimes blocks servers — try again in a minute",
            kb([HOME]))

    title = truncate(info.get("title") or info.get("description") or "", 150)
    who = info.get("uploader") or info.get("channel") or ""
    caption = f"{icon} <b>{name}</b>\n" + (f"{esc(title)}\n" if title else "") + (f"👤 {esc(who)}\n" if who else "") + f"\n🤖 via {BRAND}"
    after = kb([[btn("📸 Another link", "nav:social"), btn("🏠 Home", "nav:home")]])
    size = info.get("filesize") or info.get("filesize_approx") or 0
    headers = info.get("http_headers") or {}
    if not size or size <= MAX_UPLOAD:
        try:
            blob = download_bytes(direct, MAX_UPLOAD, headers)
            ext = "." + (info.get("ext") or "mp4")
            fn = _safe_name(f"{name}_{info.get('id', 'video')}", ext)
            sender = tg.send_video if ext == ".mp4" else tg.send_document
            res = sender(chat_id, fn, blob, caption, after)
            if not res.get("ok") and sender is tg.send_video:
                res = tg.send_document(chat_id, fn, blob, caption, after)
            if res.get("ok"):
                return _clear()
        except Exception:
            pass
    _clear()
    tg.send(chat_id, caption + "\n\n⚠️ Too big to send here — use the button:",
            kb([[btn("⬇️ Download video", url=direct)], HOME]))
