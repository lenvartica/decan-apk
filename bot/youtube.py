"""YouTube search + audio (M4A) / video (MP4) download via yt-dlp — no API key needed."""
import re
from datetime import datetime

from . import tg
from .ui import HOME, btn, kb
from .util import download_bytes, esc, fmt_dur, fmt_num, truncate, ytdlp_opts

BRAND = "Decan Bot"
MAX_UPLOAD = 48 * 1024 * 1024  # Telegram bots can upload up to 50 MB
LONG_SECONDS = 90 * 60
ID_RE = re.compile(
    r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:[^\s&]*&)*v=|shorts/|live/|embed/|v/))([A-Za-z0-9_-]{11})")


def video_id_of(text):
    m = ID_RE.search(text or "")
    return m.group(1) if m else None


def _ydl(opts, query):
    import yt_dlp  # imported lazily

    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(query, download=False)


def _err_msg(err):
    s = str(err).lower()
    if any(k in s for k in ("sign in", "bot", "429", "403", "confirm")):
        return ("⚠️ YouTube is blocking requests from this server (common on cloud hosts).\n\n"
                "<i>Bot owner:</i> add <code>YTDLP_COOKIES</code> in Vercel (see README), "
                "or run the bot on a VPS / home PC.")
    return "⚠️ Couldn't get that video. It may be private, age-restricted or removed."


def _safe_name(s, ext):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")[:80] + ext


def _again(mode):
    return btn("🔍 Search again", "go:music" if mode == "a" else "go:ytvideo")


# ─────────────── search ───────────────
def search(chat_id, query, mode="a"):
    tg.action(chat_id, "typing")
    try:
        res = _ydl(ytdlp_opts(extract_flat=True), f"ytsearch8:{query}")
        entries = [e for e in (res.get("entries") or []) if e and len(str(e.get("id", ""))) == 11]
    except Exception as e:
        return tg.send(chat_id, _err_msg(e), kb([HOME]))
    if not entries:
        return tg.send(chat_id, f"😕 Nothing found for <b>{esc(query)}</b>.", kb([[_again(mode)], HOME]))
    lines, rows = [f"{'🎵' if mode == 'a' else '▶️'} Results for <b>{esc(query)}</b>:\n"], []
    for i, e in enumerate(entries, 1):
        title = e.get("title") or "Untitled"
        who = e.get("channel") or e.get("uploader") or ""
        lines.append(f"{i}. <b>{esc(truncate(title, 70))}</b>\n    👤 {esc(who)} • ⏱ {fmt_dur(e.get('duration'))} • 👁 {fmt_num(e.get('view_count'))}")
        rows.append([btn(truncate(f"{i}. {title}", 48), f"yt:{e['id']}:{mode}")])
    rows.append([_again(mode), btn("🏠 Home", "nav:home")])
    lines.append("\nTap one to see its poster, stats and download options 👇")
    tg.send(chat_id, "\n".join(lines), kb(rows))


# ─────────────── info card (poster + views + likes) ───────────────
def card(chat_id, vid, mode="v"):
    tg.action(chat_id, "typing")
    try:
        info = _ydl(ytdlp_opts(format="best/bestaudio", ignore_no_formats_error=True),
                    f"https://www.youtube.com/watch?v={vid}")
    except Exception as e:
        return tg.send(chat_id, _err_msg(e), kb([HOME]))
    date = ""
    try:
        date = datetime.strptime(info.get("upload_date", ""), "%Y%m%d").strftime("%d %b %Y")
    except ValueError:
        pass
    dur = info.get("duration")
    caption = (
        f"{'🎵' if mode == 'a' else '🎬'} <b>{esc(truncate(info.get('title'), 180))}</b>\n"
        f"👤 {esc(info.get('channel') or info.get('uploader') or '')}\n\n"
        f"👁 Views: <b>{fmt_num(info.get('view_count'))}</b>   👍 Likes: <b>{fmt_num(info.get('like_count'))}</b>\n"
        f"💬 Comments: {fmt_num(info.get('comment_count'))}   ⏱ {fmt_dur(dur)}"
        + (f"   📅 {date}" if date else "")
        + ("\n\n⚠️ <i>Long video — the file may exceed Telegram's 50 MB limit.</i>"
           if dur and dur > LONG_SECONDS else "")
    )
    a, v = btn("🎵 Audio (M4A)", f"ya:{vid}"), btn("🎬 Video (MP4)", f"yv:{vid}")
    rows = [[a, v] if mode == "a" else [v, a],
            [btn("▶️ Watch on YouTube", url=f"https://youtu.be/{vid}")],
            [_again(mode), btn("🏠 Home", "nav:home")]]
    poster = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    if not tg.send_photo(chat_id, poster, caption[:1000], kb(rows)).get("ok"):
        tg.send(chat_id, caption, kb(rows))


# ─────────────── download ───────────────
def send_media(chat_id, vid, kind):
    audio = kind == "a"
    fmt = "bestaudio[ext=m4a]/bestaudio" if audio else "best[ext=mp4][height<=720]/best[ext=mp4]/best"
    status = tg.send(chat_id, f"⏳ Preparing your {'audio' if audio else 'video'}…")
    sid = (status.get("result") or {}).get("message_id")

    def done():
        if sid:
            tg.delete(chat_id, sid)

    def too_big():
        done()
        tg.send(chat_id,
                "📦 That file is over Telegram's 50 MB bot limit.\n"
                + ("Try the <b>audio</b> version or a shorter video." if not audio else "Try a shorter track."),
                kb([[btn("▶️ Watch on YouTube", url=f"https://youtu.be/{vid}")], HOME]))

    try:
        info = _ydl(ytdlp_opts(format=fmt), f"https://www.youtube.com/watch?v={vid}")
        direct = None if info.get("requested_formats") else info.get("url")
        if not direct:
            raise ValueError("no single-file format available")
    except Exception as e:
        done()
        return tg.send(chat_id, _err_msg(e), kb([HOME]))

    size = info.get("filesize") or info.get("filesize_approx") or 0
    if size > MAX_UPLOAD:
        return too_big()
    try:
        blob = download_bytes(direct, MAX_UPLOAD, info.get("http_headers"))
    except ValueError:
        return too_big()
    except Exception:
        done()
        return tg.send(chat_id, "⚠️ Download failed. Please try again.", kb([HOME]))

    title = info.get("title") or vid
    who = info.get("uploader") or info.get("channel") or ""
    caption = (
        f"{'🎵' if audio else '🎬'} <b>{esc(truncate(title, 150))}</b>\n👤 {esc(who)}\n"
        f"⏱ {fmt_dur(info.get('duration'))} • 👁 {fmt_num(info.get('view_count'))} • 👍 {fmt_num(info.get('like_count'))}\n\n"
        f"🤖 via {BRAND}"
    )
    ext = info.get("ext") or ("m4a" if audio else "mp4")
    fname = _safe_name(title, "." + ext)
    after = kb([[btn("🎵 More music", "go:music"), btn("▶️ More videos", "go:ytvideo")], HOME])
    if audio:
        res = tg.send_audio(chat_id, fname, blob, caption, title[:60], who[:60], after)
    else:
        res = (tg.send_video if ext == "mp4" else tg.send_document)(chat_id, fname, blob, caption, after)
        if not res.get("ok") and ext == "mp4":
            res = tg.send_document(chat_id, fname, blob, caption, after)
    done()
    if not res.get("ok"):
        tg.send(chat_id, "⚠️ Couldn't send the file to Telegram.", kb([HOME]))


def handle_text(chat_id, text, mode="a"):
    """A pasted YouTube link opens its card; anything else is a search."""
    vid = video_id_of(text)
    return card(chat_id, vid, mode) if vid else search(chat_id, text, mode)
