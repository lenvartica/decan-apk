"""Menus, screens and prompt texts — the look & feel of the bot."""
import os


def btn(text, data=None, url=None):
    b = {"text": text}
    if url:
        b["url"] = url
    else:
        b["callback_data"] = data
    return b


def kb(rows):
    return {"inline_keyboard": rows}


SITE_URL = "https://www.decankonnect.co.ke"
WHATSAPP_URL = "https://wa.me/254758176628?text=Hello%20Decan%20Konnect"
LINE = "━━━━━━━━━━━━━━━━━━━━"

HOME = [btn("🏠 Home", "nav:home")]


def back(to="home"):
    return [btn("⬅️ Back", f"nav:{to}"), btn("🏠 Home", "nav:home")]


def channel_row():
    link = os.environ.get("CHANNEL_LINK", "").strip()
    return [[btn("📢 Join our channel", url=link)]] if link else []


CITIES = [
    ("🇰🇪 Nairobi", "Africa/Nairobi"), ("🇳🇬 Lagos", "Africa/Lagos"),
    ("🇿🇦 Johannesburg", "Africa/Johannesburg"), ("🇬🇧 London", "Europe/London"),
    ("🇦🇪 Dubai", "Asia/Dubai"), ("🇮🇳 Mumbai", "Asia/Kolkata"),
    ("🇨🇳 Beijing", "Asia/Shanghai"), ("🇯🇵 Tokyo", "Asia/Tokyo"),
    ("🇺🇸 New York", "America/New_York"), ("🇺🇸 Los Angeles", "America/Los_Angeles"),
]

# Force-reply prompts keep the bot stateless: the text of the prompt that a user
# replies to tells us which tool the reply is for.
PROMPTS = {
    "apk": "📱 APK Store\nSend the name of the app you want (e.g. WhatsApp, TikTok, Spotify).",
    "music": "🎵 Music (YouTube)\nSend a song or artist name — or paste a YouTube link.",
    "ytvideo": "▶️ YouTube Video\nSend a video name — or paste a YouTube link.",
    "movie": "🎬 Movies (Internet Archive)\nSend a movie title.",
    "ig": "📸 Instagram\nPaste the link of a public reel or video.",
    "fb": "📘 Facebook\nPaste the link of a public video or reel.",
    "tt": "🎵 TikTok\nPaste the TikTok video link.",
    "tw": "🐦 X / Twitter\nPaste the link of a post that has a video.",
    "weather": "🌤 Weather\nSend a city name (e.g. Nairobi).",
    "currency": "💱 Currency Converter\nSend an amount and two currency codes, e.g.:  100 USD KES",
    "crypto": "💰 Crypto Prices\nSend a coin name (e.g. bitcoin) or type: top",
    "short": "🔗 URL Shortener\nSend the link you want to shorten.",
    "qr": "📱 QR Code\nSend any text or link to turn into a QR code.",
    "calc": "🧮 Calculator\nSend an expression, e.g.:  (25*4)+12/3",
    "dict": "📖 Dictionary\nSend an English word.",
    "country": "🌍 Country Info\nSend a country name (e.g. Kenya).",
}
REVERSE = {v: k for k, v in PROMPTS.items()}


def _home():
    text = (
        "⚡ <b>D E C A N   B O T</b> ⚡\n"
        f"{LINE}\n"
        "<i>APKs • YouTube • Movies • Social Video • Tools • Tech News</i>\n\n"
        "Welcome! Pick a section below 👇\n\n"
        "💡 <i>Tip: just type an app name, or paste an Instagram / Facebook / TikTok link.</i>"
    )
    rows = [
        [btn("📱 APK Store", "nav:apk"), btn("🎵 Music", "nav:music")],
        [btn("▶️ YouTube", "nav:yt"), btn("🎬 Movies", "nav:movies")],
        [btn("📸 Social Video", "nav:social"), btn("🛠 Tools", "nav:tools")],
        [btn("🎮 Games & Fun", "nav:fun"), btn("📰 Tech News", "nav:news")],
        [btn("🌐 Decan Konnect", "nav:site")],
        [btn("ℹ️ About", "act:about"), btn("❓ Help", "act:help")],
    ] + channel_row()
    return text, kb(rows)


def _apk():
    text = (
        "📱 <b>APK Store</b>\n"
        f"{LINE}\n"
        "Search thousands of Android apps and get the APK file right here in chat.\n\n"
        "🔥 <b>Quick search:</b>"
    )
    q = lambda n: btn(n, f"q:{n.lower()}")
    rows = [
        [btn("🔍 Search an app", "go:apk")],
        [q("WhatsApp"), q("TikTok"), q("Spotify")],
        [q("Telegram"), q("Instagram"), q("Facebook")],
        back("home"),
    ]
    return text, kb(rows)


def _music():
    text = (
        "🎵 <b>Music</b>\n"
        f"{LINE}\n"
        "Search any song or artist on <b>YouTube</b> and get the audio file in chat (M4A), "
        "with poster, views and likes.\n"
        "Or just paste a YouTube link.\n\n"
        "🔥 <b>Quick picks:</b>"
    )
    q = lambda label, term: btn(label, f"qm:{term}")
    rows = [
        [btn("🔍 Search a song / artist", "go:music")],
        [q("🌍 Afrobeats", "afrobeats 2026"), q("🎤 Hip-hop", "hip hop hits"), q("🎸 Rock", "rock classics")],
        [q("🎹 Chill", "chill lofi"), q("💃 Amapiano", "amapiano"), q("🎷 Gospel", "gospel worship")],
        back("home"),
    ]
    return text, kb(rows)


def _yt():
    text = (
        "▶️ <b>YouTube</b>\n"
        f"{LINE}\n"
        "Search videos, see the poster, views and likes, then download as <b>MP4 video</b> or <b>M4A audio</b>.\n"
        "Or paste any YouTube link in the chat.\n\n"
        "<i>Only download content you have the right to save — YouTube's terms and copyright apply.</i>"
    )
    q = lambda label, term: btn(label, f"qy:{term}")
    rows = [
        [btn("🔍 Search a video", "go:ytvideo")],
        [q("🔥 Trending", "trending today"), q("😂 Comedy", "comedy skits")],
        [q("🎓 Coding", "coding tutorial"), q("📱 Tech reviews", "tech review 2026")],
        back("home"),
    ]
    return text, kb(rows)


def _movies():
    text = (
        "🎬 <b>Movies</b>\n"
        f"{LINE}\n"
        "Search the <b>Internet Archive</b> film library. Each movie shows its poster, "
        "views, favorites and ratings — with <b>watch online</b> and <b>download MP4</b> buttons.\n\n"
        "🔥 <b>Browse:</b>"
    )
    q = lambda label, term: btn(label, f"qv:{term}")
    rows = [
        [btn("🔍 Search movies", "go:movie")],
        [q("🏚 Classics", "classic"), q("🚀 Sci-Fi", "science fiction"), q("😂 Comedy", "comedy")],
        [q("🕵️ Noir", "noir"), q("🤠 Western", "western"), q("👻 Horror", "horror")],
        [btn("🍿 Open Decan MovieHD", url="https://decan-moviehd.vercel.app/")],
        back("home"),
    ]
    return text, kb(rows)


def _social():
    text = (
        "📸 <b>Social Video Downloader</b>\n"
        f"{LINE}\n"
        "Download <b>public</b> videos & reels. Pick a platform — or just paste a link in the chat.\n\n"
        "<i>Only download content you have the right to save.</i>"
    )
    rows = [
        [btn("📸 Instagram", "go:ig"), btn("📘 Facebook", "go:fb")],
        [btn("🎵 TikTok", "go:tt"), btn("🐦 X / Twitter", "go:tw")],
        back("home"),
    ]
    return text, kb(rows)


def _tools():
    text = f"🛠 <b>Tools</b>\n{LINE}\nHandy everyday utilities:"
    rows = [
        [btn("🌤 Weather", "go:weather"), btn("💱 Currency", "go:currency")],
        [btn("💰 Crypto", "go:crypto"), btn("🔗 Shorten URL", "go:short")],
        [btn("📱 QR Code", "go:qr"), btn("🧮 Calculator", "go:calc")],
        [btn("🔐 Passwords", "nav:pw"), btn("🕐 World Time", "nav:tz")],
        [btn("📖 Dictionary", "go:dict"), btn("🌍 Country Info", "go:country")],
        back("home"),
    ]
    return text, kb(rows)


def _fun():
    text = f"🎮 <b>Games & Fun</b>\n{LINE}\nTap to play:"
    rows = [
        [btn("🎲", "dice:dice"), btn("🎯", "dice:dart"), btn("🏀", "dice:ball")],
        [btn("⚽", "dice:soccer"), btn("🎰", "dice:slots"), btn("🎳", "dice:bowling")],
        [btn("🪙 Flip a coin", "act:coin"), btn("🔮 Magic 8-Ball", "act:ball")],
        [btn("💡 Quote", "act:quote"), btn("😂 Joke", "act:joke")],
        back("home"),
    ]
    return text, kb(rows)


def _news():
    text = (
        "📰 <b>Tech News</b>\n"
        f"{LINE}\n"
        "Fresh headlines from top tech sources. Join our channel to get them automatically!"
    )
    rows = [
        [btn("🌍 Global headlines", "act:news_global"), btn("🇰🇪 Kenya tech", "act:news_kenya")],
    ] + channel_row() + [back("home")]
    return text, kb(rows)


def _site():
    text = (
        "🌐 <b>Decan Konnect</b>\n"
        f"{LINE}\n"
        "<i>Building Technology for the World.</i>\n"
        "Latest from our blog & photo stories, plus our platforms:"
    )
    rows = [
        [btn("📝 Latest blog posts", "act:site_blog"), btn("🖼 Latest stories", "act:site_gallery")],
        [btn("🌐 Website", url=SITE_URL), btn("💬 WhatsApp", url=WHATSAPP_URL)],
        [btn("🍿 Decan MovieHD", url="https://decan-moviehd.vercel.app/"),
         btn("🎓 Web Dev School", url="https://techswebdev.vercel.app/")],
    ] + channel_row() + [back("home")]
    return text, kb(rows)


def _pw():
    text = f"🔐 <b>Password Generator</b>\n{LINE}\nPick a style and length:"
    rows = [
        [btn("🔒 Strong 12", "pw:strong:12"), btn("🔒 Strong 16", "pw:strong:16"), btn("🔒 Strong 24", "pw:strong:24")],
        [btn("🔤 Easy 12", "pw:easy:12"), btn("🔤 Easy 16", "pw:easy:16")],
        [btn("🔢 PIN 4", "pw:pin:4"), btn("🔢 PIN 6", "pw:pin:6"), btn("🔢 PIN 8", "pw:pin:8")],
        back("tools"),
    ]
    return text, kb(rows)


def _tz():
    text = f"🕐 <b>World Time</b>\n{LINE}\nPick a city:"
    rows = [
        [btn(CITIES[i][0], f"time:{CITIES[i][1]}"), btn(CITIES[i + 1][0], f"time:{CITIES[i + 1][1]}")]
        for i in range(0, len(CITIES), 2)
    ]
    rows.append(back("tools"))
    return text, kb(rows)


_SCREENS = {
    "home": _home, "apk": _apk, "music": _music, "yt": _yt, "movies": _movies, "social": _social,
    "tools": _tools, "fun": _fun, "news": _news, "site": _site, "pw": _pw, "tz": _tz,
}


def get_screen(name):
    fn = _SCREENS.get(name)
    return fn() if fn else None
