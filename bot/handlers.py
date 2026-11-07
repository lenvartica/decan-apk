"""All Decan APK Downloader bot logic."""
import ast
import html
import operator
import re
import secrets
import string
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests

from . import tg

BRAND = "Decan APK Downloader"
APTOIDE = "https://ws75.aptoide.com/api/7"
MAX_UPLOAD = 48 * 1024 * 1024  # Telegram bot upload limit is 50 MB


# ───────────────────────── keyboards ─────────────────────────
def btn(text, data=None, url=None):
    b = {"text": text}
    if url:
        b["url"] = url
    else:
        b["callback_data"] = data
    return b


def kb(rows):
    return {"inline_keyboard": rows}


HOME_ROW = [btn("🏠 Main Menu", "menu:home")]

MAIN_MENU = kb([
    [btn("📥 APK Downloader", "menu:apk"), btn("🔍 Search Apps", "menu:apk")],
    [btn("🌤 Weather", "menu:weather"), btn("💱 Currency", "menu:currency")],
    [btn("🔗 Shorten URL", "menu:short"), btn("📱 QR Code", "menu:qr")],
    [btn("🧮 Calculator", "menu:calc"), btn("🔐 Password", "menu:password")],
    [btn("🕐 World Time", "menu:time"), btn("💡 Quote", "menu:quote")],
    [btn("😂 Joke", "menu:joke"), btn("ℹ️ About", "menu:about")],
])

# Prompts use Telegram's force-reply, so the bot stays fully stateless
# (perfect for serverless): we recognise which tool a reply belongs to
# by the text of the prompt message that was replied to.
PROMPTS = {
    "apk": "📥 APK Downloader\nSend the name of the app you want (e.g. WhatsApp, TikTok, Spotify).",
    "weather": "🌤 Weather\nSend a city name (e.g. Nairobi).",
    "currency": "💱 Currency Converter\nSend an amount and two currency codes, e.g.:  100 USD KES",
    "short": "🔗 URL Shortener\nSend the link you want to shorten.",
    "qr": "📱 QR Code\nSend any text or link to turn into a QR code.",
    "calc": "🧮 Calculator\nSend an expression, e.g.:  (25*4)+12/3",
}
REVERSE = {v: k for k, v in PROMPTS.items()}


def send_prompt(chat_id, key):
    tg.send(
        chat_id,
        PROMPTS[key],
        markup={"force_reply": True, "input_field_placeholder": "Type here…"},
        parse_mode=None,
    )


def send_menu(chat_id):
    tg.send(
        chat_id,
        f"✨ <b>{BRAND}</b>\n\nPick a tool below, or just type an app name to search for an APK.",
        MAIN_MENU,
    )


# ───────────────────────── helpers ─────────────────────────
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


def esc(s):
    return html.escape(str(s or ""))


def get_json(url, **kw):
    r = requests.get(url, timeout=15, headers={"User-Agent": "DecanBot/1.0"}, **kw)
    r.raise_for_status()
    return r.json()


# ───────────────────────── APK downloader ─────────────────────────
def apk_search(chat_id, query):
    tg.action(chat_id, "typing")
    try:
        data = get_json(f"{APTOIDE}/apps/search", params={"query": query, "limit": 8})
        apps = (data.get("datalist") or {}).get("list") or []
    except Exception:
        apps = []

    apps = [a for a in apps if a.get("package") and len(a["package"]) <= 58]
    if not apps:
        tg.send(
            chat_id,
            f"😕 No apps found for <b>{esc(query)}</b>. Try another name.",
            kb([HOME_ROW]),
        )
        return

    lines, rows = [f"🔎 Results for <b>{esc(query)}</b>:\n"], []
    for i, a in enumerate(apps, 1):
        f = a.get("file") or {}
        size = human(f.get("filesize") or a.get("size"))
        rating = ((a.get("stats") or {}).get("rating") or {}).get("avg")
        stars = f" ⭐{rating:.1f}" if isinstance(rating, (int, float)) and rating else ""
        lines.append(f"{i}. <b>{esc(a.get('name'))}</b> — v{esc(f.get('vername'))} • {size}{stars}")
        rows.append([btn(f"{i}. {a.get('name', '')[:32]} ({size})", f"dl:{a['package']}")])
    rows.append(HOME_ROW)
    lines.append("\nTap an app to download its APK 👇")
    tg.send(chat_id, "\n".join(lines), kb(rows))


def _download(url, limit):
    buf = bytearray()
    with requests.get(url, stream=True, timeout=30, headers={"User-Agent": "DecanBot/1.0"}) as r:
        r.raise_for_status()
        for chunk in r.iter_content(256 * 1024):
            buf.extend(chunk)
            if len(buf) > limit:
                raise ValueError("file too large")
    return bytes(buf)


def apk_send(chat_id, package):
    tg.action(chat_id, "typing")
    try:
        meta = get_json(f"{APTOIDE}/app/getMeta", params={"package_name": package})
        d = meta["data"]
        f = d["file"]
        url = f["path"]
    except Exception:
        tg.send(chat_id, "⚠️ Couldn't fetch that app right now. Try again or pick another.", kb([HOME_ROW]))
        return

    name = d.get("name") or package
    ver = f.get("vername") or ""
    size = f.get("filesize") or d.get("size") or 0
    rating = ((d.get("stats") or {}).get("rating") or {}).get("avg")
    downloads = (d.get("stats") or {}).get("downloads")

    caption = (
        f"📦 <b>{esc(name)}</b>\n"
        f"🆚 Version: {esc(ver)}\n"
        f"🧾 Package: <code>{esc(package)}</code>\n"
        f"💾 Size: {human(size)}\n"
        + (f"⭐ Rating: {rating:.1f}\n" if isinstance(rating, (int, float)) and rating else "")
        + (f"⬇️ Downloads: {int(downloads):,}\n" if downloads else "")
        + f"\n🤖 via {BRAND}"
    )

    # Small enough → upload the real file into the chat
    if size and size <= MAX_UPLOAD:
        status = tg.send(chat_id, f"⏳ Downloading <b>{esc(name)}</b> ({human(size)})…")
        try:
            blob = _download(url, MAX_UPLOAD)
            fname = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{name}_{ver}") + ".apk"
            res = tg.send_document(chat_id, fname, blob, caption)
            mid = (status.get("result") or {}).get("message_id")
            if mid:
                tg.delete(chat_id, mid)
            if res.get("ok"):
                tg.send(chat_id, "✅ Done! Want another app?", kb([HOME_ROW]))
                return
        except Exception:
            pass  # fall through to the link

    # Too big (or upload failed) → send a direct download button
    tg.send(
        chat_id,
        caption + "\n\n⚠️ File is too big to send here — use the button below:",
        kb([[btn(f"⬇️ Download ({human(size)})", url=url)], HOME_ROW]),
    )


# ───────────────────────── Weather ─────────────────────────
def _wx_text(code):
    if code == 0: return "Clear sky ☀️"
    if code in (1, 2): return "Partly cloudy ⛅"
    if code == 3: return "Overcast ☁️"
    if code in (45, 48): return "Foggy 🌫"
    if 51 <= code <= 57: return "Drizzle 🌦"
    if 61 <= code <= 67 or 80 <= code <= 82: return "Rain 🌧"
    if 71 <= code <= 77 or code in (85, 86): return "Snow ❄️"
    if code >= 95: return "Thunderstorm ⛈"
    return "Unknown"


def weather(chat_id, city):
    try:
        g = get_json("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1})
        place = g["results"][0]
        w = get_json(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone": "auto",
            },
        )["current"]
    except Exception:
        tg.send(chat_id, f"😕 Couldn't find weather for <b>{esc(city)}</b>.", kb([HOME_ROW]))
        return
    tg.send(
        chat_id,
        f"🌍 <b>{esc(place['name'])}, {esc(place.get('country', ''))}</b>\n\n"
        f"{_wx_text(w['weather_code'])}\n"
        f"🌡 Temp: {w['temperature_2m']}°C (feels {w['apparent_temperature']}°C)\n"
        f"💧 Humidity: {w['relative_humidity_2m']}%\n"
        f"💨 Wind: {w['wind_speed_10m']} km/h",
        kb([HOME_ROW]),
    )


# ───────────────────────── Currency ─────────────────────────
def currency(chat_id, text):
    m = re.match(r"^\s*([\d,]*\.?\d+)\s*([A-Za-z]{3})\s*(?:to|in|->|=)?\s*([A-Za-z]{3})\s*$", text)
    if not m:
        tg.send(chat_id, "Format: <code>100 USD KES</code>", kb([HOME_ROW]))
        return
    amount = float(m.group(1).replace(",", ""))
    frm, to = m.group(2).upper(), m.group(3).upper()
    try:
        data = get_json(f"https://open.er-api.com/v6/latest/{frm}")
        rate = data["rates"][to]
    except Exception:
        tg.send(chat_id, "⚠️ Unknown currency code or service unavailable.", kb([HOME_ROW]))
        return
    tg.send(
        chat_id,
        f"💱 <b>{amount:,.2f} {frm}</b> = <b>{amount * rate:,.2f} {to}</b>\n"
        f"<i>Rate: 1 {frm} = {rate:,.4f} {to}</i>",
        kb([HOME_ROW]),
    )


# ───────────────────────── URL shortener / QR ─────────────────────────
def shorten(chat_id, url):
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    try:
        data = get_json("https://is.gd/create.php", params={"format": "json", "url": url})
        short = data["shorturl"]
    except Exception:
        tg.send(chat_id, "⚠️ Couldn't shorten that link. Is it a valid URL?", kb([HOME_ROW]))
        return
    tg.send(chat_id, f"🔗 <b>Short link:</b>\n{esc(short)}", kb([HOME_ROW]))


def qr(chat_id, text):
    tg.action(chat_id, "upload_photo")
    url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&margin=10&data={quote(text)}"
    res = tg.send_photo(chat_id, url, f"📱 QR for:\n<code>{esc(text[:200])}</code>", kb([HOME_ROW]))
    if not res.get("ok"):
        tg.send(chat_id, "⚠️ Couldn't generate the QR code.", kb([HOME_ROW]))


# ───────────────────────── Calculator ─────────────────────────
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}


def _eval(n):
    if isinstance(n, ast.Expression):
        return _eval(n.body)
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
        a, b = _eval(n.left), _eval(n.right)
        if isinstance(n.op, ast.Pow) and abs(b) > 100:
            raise ValueError("exponent too large")
        return _OPS[type(n.op)](a, b)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
        v = _eval(n.operand)
        return v if isinstance(n.op, ast.UAdd) else -v
    raise ValueError("unsupported")


def calc(chat_id, expr):
    clean = expr.replace("^", "**").replace("×", "*").replace("÷", "/").replace(",", "")
    try:
        result = _eval(ast.parse(clean, mode="eval"))
        if isinstance(result, float):
            result = round(result, 10)
        tg.send(chat_id, f"🧮 <code>{esc(expr)}</code>\n= <b>{result}</b>", kb([HOME_ROW]))
    except Exception:
        tg.send(chat_id, "⚠️ Couldn't calculate that. Use numbers and + - * / ^ % ( )", kb([HOME_ROW]))


# ───────────────────────── Password ─────────────────────────
def password_menu(chat_id):
    tg.send(
        chat_id,
        "🔐 <b>Password Generator</b>\nChoose a length:",
        kb([[btn(str(n), f"pw:{n}") for n in (8, 12, 16, 24, 32)], HOME_ROW]),
    )


def password(chat_id, length):
    length = max(6, min(64, length))
    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    pw = "".join(secrets.choice(chars) for _ in range(length))
    tg.send(
        chat_id,
        f"🔐 Your {length}-character password:\n\n<code>{esc(pw)}</code>\n\n<i>Tap to copy. Never reuse passwords!</i>",
        kb([[btn("🔄 Another", f"pw:{length}")], HOME_ROW]),
    )


# ───────────────────────── World time ─────────────────────────
CITIES = [
    ("🇰🇪 Nairobi", "Africa/Nairobi"), ("🇳🇬 Lagos", "Africa/Lagos"),
    ("🇿🇦 Johannesburg", "Africa/Johannesburg"), ("🇬🇧 London", "Europe/London"),
    ("🇦🇪 Dubai", "Asia/Dubai"), ("🇮🇳 Mumbai", "Asia/Kolkata"),
    ("🇨🇳 Beijing", "Asia/Shanghai"), ("🇯🇵 Tokyo", "Asia/Tokyo"),
    ("🇺🇸 New York", "America/New_York"), ("🇺🇸 Los Angeles", "America/Los_Angeles"),
]


def time_menu(chat_id):
    rows = [
        [btn(CITIES[i][0], f"time:{CITIES[i][1]}"), btn(CITIES[i + 1][0], f"time:{CITIES[i + 1][1]}")]
        for i in range(0, len(CITIES), 2)
    ]
    rows.append(HOME_ROW)
    tg.send(chat_id, "🕐 <b>World Time</b>\nPick a city:", kb(rows))


def show_time(chat_id, tz):
    try:
        now = datetime.now(ZoneInfo(tz))
    except Exception:
        tg.send(chat_id, "⚠️ Unknown timezone.", kb([HOME_ROW]))
        return
    label = next((c[0] for c in CITIES if c[1] == tz), tz)
    tg.send(
        chat_id,
        f"🕐 <b>{esc(label)}</b>\n{now.strftime('%A, %d %B %Y')}\n<b>{now.strftime('%H:%M:%S')}</b> ({now.strftime('%Z')})",
        kb([[btn("⬅️ Other cities", "menu:time")], HOME_ROW]),
    )


# ───────────────────────── Fun ─────────────────────────
def quote_cmd(chat_id):
    try:
        q = get_json("https://zenquotes.io/api/random")[0]
        text = f"💡 <i>“{esc(q['q'])}”</i>\n— <b>{esc(q['a'])}</b>"
    except Exception:
        text = "💡 <i>“The best way to predict the future is to build it.”</i>"
    tg.send(chat_id, text, kb([[btn("🔄 Another", "menu:quote")], HOME_ROW]))


def joke_cmd(chat_id):
    try:
        j = get_json(
            "https://v2.jokeapi.dev/joke/Programming,Misc",
            params={"safe-mode": "", "blacklistFlags": "nsfw,religious,political,racist,sexist,explicit"},
        )
        if j.get("type") == "twopart":
            text = f"😂 {esc(j['setup'])}\n\n<tg-spoiler>{esc(j['delivery'])}</tg-spoiler>"
        else:
            text = f"😂 {esc(j['joke'])}"
    except Exception:
        text = "😂 Why do programmers prefer dark mode? Because light attracts bugs."
    tg.send(chat_id, text, kb([[btn("🔄 Another", "menu:joke")], HOME_ROW]))


# ───────────────────────── Info ─────────────────────────
def about(chat_id):
    tg.send(
        chat_id,
        f"ℹ️ <b>{BRAND}</b>\n\n"
        "Search and download Android APKs, plus handy everyday tools:\n"
        "weather, currency, URL shortener, QR codes, calculator, passwords, world time, quotes and jokes.\n\n"
        "⚠️ Only download apps you're allowed to use, and respect developers' licences.\n\n"
        "🛠 Built by <b>Decan Systems</b>",
        kb([HOME_ROW]),
    )


def help_cmd(chat_id):
    tg.send(
        chat_id,
        "<b>Commands</b>\n"
        "/start or /menu – main menu\n"
        "/apk &lt;name&gt; – search &amp; download APKs\n"
        "/weather &lt;city&gt;\n"
        "/currency 100 USD KES\n"
        "/short &lt;url&gt;\n"
        "/qr &lt;text&gt;\n"
        "/calc &lt;expression&gt;\n"
        "/password – generator\n"
        "/time – world clock\n"
        "/quote  /joke  /about\n\n"
        "In a private chat you can also just type an app name.",
        kb([HOME_ROW]),
    )


# ───────────────────────── routing ─────────────────────────
ACTIONS = {
    "apk": apk_search, "weather": weather, "currency": currency,
    "short": shorten, "qr": qr, "calc": calc,
}
COMMANDS = {
    "/apk": "apk", "/weather": "weather", "/currency": "currency",
    "/short": "short", "/qr": "qr", "/calc": "calc",
}


def handle_command(chat_id, cmd, arg):
    if cmd in ("/start", "/menu"):
        return send_menu(chat_id)
    if cmd == "/help":
        return help_cmd(chat_id)
    if cmd == "/about":
        return about(chat_id)
    if cmd == "/password":
        return password_menu(chat_id)
    if cmd == "/time":
        return time_menu(chat_id)
    if cmd == "/quote":
        return quote_cmd(chat_id)
    if cmd == "/joke":
        return joke_cmd(chat_id)
    key = COMMANDS.get(cmd)
    if key:
        return ACTIONS[key](chat_id, arg) if arg else send_prompt(chat_id, key)
    tg.send(chat_id, "Unknown command. Try /menu", kb([HOME_ROW]))


def handle_message(msg):
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    if not text:
        return
    if text.startswith("/"):
        cmd, _, arg = text.partition(" ")
        return handle_command(chat_id, cmd.split("@")[0].lower(), arg.strip())

    replied = (msg.get("reply_to_message") or {}).get("text")
    key = REVERSE.get(replied)
    if key:
        return ACTIONS[key](chat_id, text)
    if msg["chat"].get("type") == "private":
        return apk_search(chat_id, text)


def handle_callback(cq):
    tg.answer_cb(cq["id"])
    msg = cq.get("message")
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    kind, _, val = (cq.get("data") or "").partition(":")

    if kind == "menu":
        if val == "home": return send_menu(chat_id)
        if val in PROMPTS: return send_prompt(chat_id, val)
        if val == "password": return password_menu(chat_id)
        if val == "time": return time_menu(chat_id)
        if val == "quote": return quote_cmd(chat_id)
        if val == "joke": return joke_cmd(chat_id)
        if val == "about": return about(chat_id)
    elif kind == "dl":
        return apk_send(chat_id, val)
    elif kind == "pw" and val.isdigit():
        return password(chat_id, int(val))
    elif kind == "time":
        return show_time(chat_id, val)


def handle_update(update):
    if "message" in update:
        handle_message(update["message"])
    elif "callback_query" in update:
        handle_callback(update["callback_query"])
