"""Routing: commands, menu buttons, force-reply prompts, admin tools."""
import os
import re
import time

from . import downloaders as dl
from . import news, store, tg, tools, ui
from . import youtube as yt
from .ui import HOME, btn, kb

URL_RE = re.compile(r"https?://\S+")


def is_admin(user_id):
    ids = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
    return str(user_id) in ids


# ───────────────────────── screens & prompts ─────────────────────────
def send_home(chat_id):
    text, markup = ui.get_screen("home")
    tg.send(chat_id, text, markup)


def show_screen(chat_id, message_id, name):
    scr = ui.get_screen(name)
    if not scr:
        return
    text, markup = scr
    r = tg.edit(chat_id, message_id, text, markup)  # edit in place = app-like feel
    if not r.get("ok") and "not modified" not in str(r.get("description", "")):
        tg.send(chat_id, text, markup)


def send_prompt(chat_id, key):
    tg.send(chat_id, ui.PROMPTS[key],
            markup={"force_reply": True, "input_field_placeholder": "Type here…"}, parse_mode=None)


def about(chat_id):
    tg.send(
        chat_id,
        "ℹ️ <b>Decan Bot</b>\n" + ui.LINE + "\n"
        "📱 APK Store • 🎵 YouTube music & video • 🎬 Archive.org movies • 📸 Instagram/Facebook/TikTok/X videos\n"
        "🛠 Weather, currency, crypto, QR, passwords, dictionary & more\n"
        "📰 Daily tech news and updates from Decan Konnect\n\n"
        "⚠️ Only download content you have the right to use.\n\n"
        "🛠 Built by <b>Decan Systems</b> • Decan Konnect — <i>Building Technology for the World.</i>",
        kb([[btn("🌐 decankonnect.co.ke", url=ui.SITE_URL)], HOME]),
    )


def help_cmd(chat_id):
    tg.send(
        chat_id,
        "❓ <b>Help</b>\n" + ui.LINE + "\n"
        "<b>Just chat:</b> type an app name, or paste a YouTube / Instagram / Facebook / TikTok / X link.\n\n"
        "<b>Commands</b>\n"
        "/menu – main menu\n"
        "/apk &lt;name&gt; • /music &lt;song&gt; • /yt &lt;video or link&gt; • /movie &lt;title&gt;\n"
        "/ig • /fb • /tiktok • /x &lt;link&gt;\n"
        "/weather • /currency 100 USD KES • /crypto • /short • /qr • /calc\n"
        "/password • /time • /dict • /country\n"
        "/news • /blog • /gallery\n"
        "/dice • /coin • /8ball • /quote • /joke • /about",
        kb([HOME]),
    )


# ───────────────────────── tables ─────────────────────────
ACTIONS = {  # force-reply key -> function(chat_id, text)
    "apk": dl.apk_search, "movie": dl.movie_search,
    "music": lambda c, t: yt.handle_text(c, t, "a"), "ytvideo": lambda c, t: yt.handle_text(c, t, "v"),
    "ig": dl.social, "fb": dl.social, "tt": dl.social, "tw": dl.social,
    "weather": tools.weather, "currency": tools.currency, "crypto": tools.crypto, "short": tools.shorten,
    "qr": tools.qr, "calc": tools.calc, "dict": tools.dictionary, "country": tools.country,
}
PROMPT_CMDS = {
    "/apk": "apk", "/music": "music", "/yt": "ytvideo", "/youtube": "ytvideo", "/movie": "movie",
    "/ig": "ig", "/instagram": "ig", "/fb": "fb", "/facebook": "fb", "/tiktok": "tt", "/x": "tw",
    "/weather": "weather", "/currency": "currency", "/short": "short", "/qr": "qr", "/calc": "calc",
    "/dict": "dict", "/country": "country",
}
SIMPLE = {  # commands/acts that need no input
    "joke": tools.joke, "quote": tools.quote_cmd, "coin": tools.coin, "ball": tools.ball,
    "news_global": lambda c: news.headlines_message(c, "global"),
    "news_kenya": lambda c: news.headlines_message(c, "kenya"),
    "site_blog": lambda c: news.send_site_latest(c, "blog"),
    "site_gallery": lambda c: news.send_site_latest(c, "gallery"),
    "about": about, "help": help_cmd,
}
SIMPLE_CMDS = {
    "/joke": "joke", "/quote": "quote", "/coin": "coin", "/8ball": "ball", "/news": "news_global",
    "/blog": "site_blog", "/gallery": "site_gallery", "/about": "about", "/help": "help",
}


# ───────────────────────── admin ─────────────────────────
def admin_command(chat_id, cmd, arg):
    if cmd == "/stats":
        if not store.available():
            return tg.send(chat_id, "📊 Stats need Redis (Upstash / Vercel KV) to be connected.")
        return tg.send(chat_id, f"📊 <b>Stats</b>\n👥 Users: {store.scard('decan:users')}\n"
                                f"📰 Channel posts logged: {store.scard('decan:posted')}")
    if cmd == "/broadcast":
        if not arg:
            return tg.send(chat_id, "Usage: <code>/broadcast your message</code>")
        sent = 0
        for uid in store.smembers("decan:users")[:500]:
            if tg.send(int(uid), arg, parse_mode=None).get("ok"):
                sent += 1
            time.sleep(0.05)
        return tg.send(chat_id, f"📣 Broadcast delivered to {sent} users.")
    if cmd == "/postnow":
        only = arg.strip().lower() if arg.strip().lower() in ("news", "site") else "all"
        tg.send(chat_id, f"⏳ Posting ({only}) to channels…")
        return tg.send(chat_id, f"<pre>{news.esc(str(news.run_cron(only)))}</pre>")


# ───────────────────────── message / callback ─────────────────────────
def handle_command(chat_id, cmd, arg, msg):
    if cmd in ("/start", "/menu"):
        return send_home(chat_id)
    if cmd in ("/stats", "/broadcast", "/postnow"):
        if is_admin((msg.get("from") or {}).get("id")):
            return admin_command(chat_id, cmd, arg)
        return tg.send(chat_id, "🔒 Admins only.")
    if cmd == "/password":
        text, markup = ui.get_screen("pw")
        return tg.send(chat_id, text, markup)
    if cmd == "/time":
        text, markup = ui.get_screen("tz")
        return tg.send(chat_id, text, markup)
    if cmd == "/dice":
        return tools.dice(chat_id, "dice")
    if cmd == "/crypto":
        return tools.crypto(chat_id, arg or "top")
    if cmd in SIMPLE_CMDS:
        return SIMPLE[SIMPLE_CMDS[cmd]](chat_id)
    key = PROMPT_CMDS.get(cmd)
    if key:
        return ACTIONS[key](chat_id, arg) if arg else send_prompt(chat_id, key)
    tg.send(chat_id, "Unknown command. Try /menu", kb([HOME]))


def handle_message(msg):
    chat = msg["chat"]
    chat_id = chat["id"]
    if chat.get("type") == "private":
        store.sadd("decan:users", chat_id)
    text = (msg.get("text") or "").strip()
    if not text:
        return
    if text.startswith("/"):
        cmd, _, arg = text.partition(" ")
        return handle_command(chat_id, cmd.split("@")[0].lower(), arg.strip(), msg)

    key = ui.REVERSE.get((msg.get("reply_to_message") or {}).get("text"))
    if key:
        return ACTIONS[key](chat_id, text)
    vid = yt.video_id_of(text)
    if vid:
        return yt.card(chat_id, vid, "v")
    m = URL_RE.search(text)
    if m and dl.platform_of(m.group(0)):
        return dl.social(chat_id, text)
    if chat.get("type") == "private":
        return dl.apk_search(chat_id, text)


def handle_callback(cq):
    tg.answer_cb(cq["id"])
    msg = cq.get("message")
    if not msg:
        return
    chat_id, mid = msg["chat"]["id"], msg["message_id"]
    kind, _, val = (cq.get("data") or "").partition(":")

    if kind == "nav":
        return show_screen(chat_id, mid, val)
    if kind == "go" and val in ui.PROMPTS:
        return send_prompt(chat_id, val)
    if kind == "act" and val in SIMPLE:
        return SIMPLE[val](chat_id)
    if kind == "q":
        return dl.apk_search(chat_id, val)
    if kind == "qm":
        return yt.search(chat_id, val, "a")
    if kind == "qy":
        return yt.search(chat_id, val, "v")
    if kind == "yt":
        vid, _, mode = val.partition(":")
        return yt.card(chat_id, vid, mode or "v")
    if kind == "ya":
        return yt.send_media(chat_id, val, "a")
    if kind == "yv":
        return yt.send_media(chat_id, val, "v")
    if kind == "qv":
        return dl.movie_search(chat_id, val)
    if kind == "dl":
        return dl.apk_send(chat_id, val)
    if kind == "mv":
        return dl.movie_send(chat_id, val)
    if kind == "pw":
        mode, _, length = val.partition(":")
        return tools.password(chat_id, mode, int(length) if length.isdigit() else 16)
    if kind == "time":
        return tools.show_time(chat_id, val)
    if kind == "dice":
        return tools.dice(chat_id, val)


def handle_update(update):
    if "message" in update:
        handle_message(update["message"])
    elif "callback_query" in update:
        handle_callback(update["callback_query"])
