"""Visit  https://YOUR-APP.vercel.app/api/setup?key=WEBHOOK_SECRET  once after deploying.
Registers the webhook and the command list with Telegram."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot import tg  # noqa: E402

COMMANDS = [
    ("menu", "Open the main menu"),
    ("apk", "Search & download an APK"),
    ("weather", "Weather for a city"),
    ("currency", "Convert currency"),
    ("short", "Shorten a URL"),
    ("qr", "Make a QR code"),
    ("calc", "Calculator"),
    ("password", "Password generator"),
    ("time", "World time"),
    ("quote", "Random quote"),
    ("joke", "Random joke"),
    ("help", "Help"),
    ("about", "About this bot"),
]


class handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj, indent=2).encode())

    def do_GET(self):
        secret = os.environ.get("WEBHOOK_SECRET", "")
        key = parse_qs(urlparse(self.path).query).get("key", [""])[0]
        if not secret or key != secret:
            return self._json(403, {"error": "bad or missing key"})
        host = self.headers.get("x-forwarded-host") or self.headers.get("host")
        url = f"https://{host}/api/webhook"
        hook = tg.call(
            "setWebhook",
            url=url,
            secret_token=secret,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
        cmds = tg.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in COMMANDS])
        self._json(200, {"webhook_url": url, "setWebhook": hook, "setMyCommands": cmds})
