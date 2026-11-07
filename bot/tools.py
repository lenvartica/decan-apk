"""Everyday utility tools."""
import ast
import operator
import random
import re
import secrets
import string
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from . import tg
from .ui import CITIES, HOME, back, btn, kb
from .util import esc, get_json

DICE = {"dice": "🎲", "dart": "🎯", "ball": "🏀", "soccer": "⚽", "slots": "🎰", "bowling": "🎳"}


# ── Weather ──
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
                "latitude": place["latitude"], "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone": "auto",
            },
        )["current"]
    except Exception:
        return tg.send(chat_id, f"😕 Couldn't find weather for <b>{esc(city)}</b>.", kb([HOME]))
    tg.send(
        chat_id,
        f"🌍 <b>{esc(place['name'])}, {esc(place.get('country', ''))}</b>\n\n"
        f"{_wx_text(w['weather_code'])}\n"
        f"🌡 Temp: {w['temperature_2m']}°C (feels {w['apparent_temperature']}°C)\n"
        f"💧 Humidity: {w['relative_humidity_2m']}%\n"
        f"💨 Wind: {w['wind_speed_10m']} km/h",
        kb([[btn("🌤 Another city", "go:weather")], HOME]),
    )


# ── Currency / crypto ──
def currency(chat_id, text):
    m = re.match(r"^\s*([\d,]*\.?\d+)\s*([A-Za-z]{3})\s*(?:to|in|->|=)?\s*([A-Za-z]{3})\s*$", text)
    if not m:
        return tg.send(chat_id, "Format: <code>100 USD KES</code>", kb([HOME]))
    amount = float(m.group(1).replace(",", ""))
    frm, to = m.group(2).upper(), m.group(3).upper()
    try:
        rate = get_json(f"https://open.er-api.com/v6/latest/{frm}")["rates"][to]
    except Exception:
        return tg.send(chat_id, "⚠️ Unknown currency code or service unavailable.", kb([HOME]))
    tg.send(
        chat_id,
        f"💱 <b>{amount:,.2f} {frm}</b> = <b>{amount * rate:,.2f} {to}</b>\n"
        f"<i>Rate: 1 {frm} = {rate:,.4f} {to}</i>",
        kb([[btn("💱 Convert again", "go:currency")], HOME]),
    )


TOP_COINS = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple", "dogecoin"]


def crypto(chat_id, text):
    q = (text or "").strip().lower()
    try:
        if q in ("", "top"):
            ids = TOP_COINS
        else:
            ids = [get_json("https://api.coingecko.com/api/v3/search", params={"query": q})["coins"][0]["id"]]
        d = get_json(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ",".join(ids), "vs_currencies": "usd,kes", "include_24hr_change": "true"},
        )
    except Exception:
        return tg.send(chat_id, "⚠️ Couldn't fetch crypto prices right now.", kb([HOME]))
    lines = ["💰 <b>Crypto prices</b>\n"]
    for i in ids:
        p = d.get(i)
        if not p:
            continue
        ch = p.get("usd_24h_change") or 0
        usd = f"${p['usd']:,.2f}" if p["usd"] >= 1 else f"${p['usd']:,.6f}"
        lines.append(
            f"<b>{esc(i.title())}</b>\n   {usd} • KES {p.get('kes', 0):,.0f}  "
            f"{'🟢▲' if ch >= 0 else '🔴▼'} {abs(ch):.2f}%"
        )
    tg.send(chat_id, "\n".join(lines), kb([[btn("🔄 Top coins", "go:crypto")], HOME]))


# ── Short URL / QR ──
def shorten(chat_id, url):
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    try:
        short = get_json("https://is.gd/create.php", params={"format": "json", "url": url})["shorturl"]
    except Exception:
        return tg.send(chat_id, "⚠️ Couldn't shorten that link. Is it a valid URL?", kb([HOME]))
    tg.send(chat_id, f"🔗 <b>Short link:</b>\n{esc(short)}", kb([HOME]))


def qr(chat_id, text):
    tg.action(chat_id, "upload_photo")
    url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&margin=10&data={quote(text)}"
    res = tg.send_photo(chat_id, url, f"📱 QR for:\n<code>{esc(text[:200])}</code>", kb([HOME]))
    if not res.get("ok"):
        tg.send(chat_id, "⚠️ Couldn't generate the QR code.", kb([HOME]))


# ── Calculator ──
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
        tg.send(chat_id, f"🧮 <code>{esc(expr)}</code>\n= <b>{result}</b>", kb([[btn("🧮 Again", "go:calc")], HOME]))
    except Exception:
        tg.send(chat_id, "⚠️ Couldn't calculate that. Use numbers and + - * / ^ % ( )", kb([HOME]))


# ── Passwords ──
def password(chat_id, mode, length):
    if mode == "pin":
        length = max(4, min(12, length))
        pw = "".join(secrets.choice(string.digits) for _ in range(length))
        label = f"{length}-digit PIN"
    else:
        length = max(8, min(64, length))
        if mode == "easy":
            chars = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            label = f"{length}-character easy-to-type password"
            while True:
                pw = "".join(secrets.choice(chars) for _ in range(length))
                if any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw):
                    break
        else:
            sym = "!@#$%^&*()-_=+"
            chars = string.ascii_letters + string.digits + sym
            label = f"{length}-character strong password"
            while True:
                pw = "".join(secrets.choice(chars) for _ in range(length))
                if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                        and any(c.isdigit() for c in pw) and any(c in sym for c in pw)):
                    break
    tg.send(
        chat_id,
        f"🔐 Your {label}:\n\n<code>{esc(pw)}</code>\n\n<i>Tap to copy. Never reuse passwords!</i>",
        kb([[btn("🔄 Another", f"pw:{mode}:{length}"), btn("🎛 Styles", "nav:pw")], HOME]),
    )


# ── World time ──
def show_time(chat_id, tz):
    try:
        now = datetime.now(ZoneInfo(tz))
    except Exception:
        return tg.send(chat_id, "⚠️ Unknown timezone.", kb([HOME]))
    label = next((c[0] for c in CITIES if c[1] == tz), tz)
    tg.send(
        chat_id,
        f"🕐 <b>{esc(label)}</b>\n{now.strftime('%A, %d %B %Y')}\n<b>{now.strftime('%H:%M:%S')}</b> ({now.strftime('%Z')})",
        kb([[btn("⬅️ Other cities", "nav:tz")], HOME]),
    )


# ── Dictionary / country ──
def dictionary(chat_id, word):
    w = (word.strip().split() or [""])[0]
    try:
        e = get_json(f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(w)}")[0]
    except Exception:
        return tg.send(chat_id, f"📖 No definition found for <b>{esc(w)}</b>.", kb([HOME]))
    lines = [f"📖 <b>{esc(e.get('word', w))}</b>  <i>{esc(e.get('phonetic', ''))}</i>\n"]
    for m in e.get("meanings", [])[:3]:
        d = (m.get("definitions") or [{}])[0]
        lines.append(f"<b>{esc(m.get('partOfSpeech', ''))}</b> — {esc(d.get('definition', ''))}")
        if d.get("example"):
            lines.append(f"   <i>“{esc(d['example'])}”</i>")
    tg.send(chat_id, "\n".join(lines), kb([[btn("📖 Another word", "go:dict")], HOME]))


def _flag(cca2):
    try:
        return "".join(chr(0x1F1E6 + ord(c) - 65) for c in cca2.upper())
    except Exception:
        return "🏳"


def country(chat_id, name):
    try:
        data = get_json(
            f"https://restcountries.com/v3.1/name/{quote(name.strip())}",
            params={"fields": "name,capital,region,subregion,population,area,currencies,languages,cca2"},
        )
        c = next((x for x in data if x["name"]["common"].lower() == name.strip().lower()), data[0])
    except Exception:
        return tg.send(chat_id, f"🌍 Couldn't find <b>{esc(name)}</b>.", kb([HOME]))
    cur = ", ".join(f"{v.get('name')} ({k})" for k, v in (c.get("currencies") or {}).items())
    langs = ", ".join((c.get("languages") or {}).values())
    tg.send(
        chat_id,
        f"{_flag(c.get('cca2', ''))} <b>{esc(c['name']['common'])}</b>\n"
        f"🏛 Capital: {esc(', '.join(c.get('capital') or ['—']))}\n"
        f"🗺 Region: {esc(c.get('subregion') or c.get('region'))}\n"
        f"👥 Population: {c.get('population', 0):,}\n"
        f"📐 Area: {c.get('area', 0):,.0f} km²\n"
        f"💵 Currency: {esc(cur)}\n"
        f"🗣 Languages: {esc(langs)}",
        kb([[btn("🌍 Another country", "go:country")], HOME]),
    )


# ── Fun ──
def dice(chat_id, key):
    tg.send_dice(chat_id, DICE.get(key, "🎲"))


def coin(chat_id):
    tg.send(chat_id, f"🪙 <b>{random.choice(['HEADS', 'TAILS'])}</b>!", kb([[btn("🪙 Flip again", "act:coin")], HOME]))


BALL = ["Yes, definitely! ✅", "It is certain. ✨", "Most likely. 👍", "Ask again later. 🔄",
        "Cannot predict now. 🌫", "Don't count on it. ❌", "My sources say no. 🚫", "Very doubtful. 😬",
        "Signs point to yes. 🔮"]


def ball(chat_id):
    tg.send(chat_id, f"🔮 {random.choice(BALL)}", kb([[btn("🔮 Ask again", "act:ball")], HOME]))


def quote_cmd(chat_id):
    try:
        q = get_json("https://zenquotes.io/api/random")[0]
        text = f"💡 <i>“{esc(q['q'])}”</i>\n— <b>{esc(q['a'])}</b>"
    except Exception:
        text = "💡 <i>“The best way to predict the future is to build it.”</i>"
    tg.send(chat_id, text, kb([[btn("🔄 Another", "act:quote")], HOME]))


def joke(chat_id):
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
    tg.send(chat_id, text, kb([[btn("🔄 Another", "act:joke")], HOME]))
