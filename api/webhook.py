import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot.handlers import handle_update  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _reply(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        self._reply(200, "Decan APK Downloader bot is running ✅")

    def do_POST(self):
        secret = os.environ.get("WEBHOOK_SECRET")
        if secret and self.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
            return self._reply(403, "forbidden")
        try:
            length = int(self.headers.get("Content-Length", 0))
            update = json.loads(self.rfile.read(length) or b"{}")
            handle_update(update)
        except Exception:
            traceback.print_exc()  # visible in Vercel logs
        # Always 200 so Telegram doesn't retry-spam on errors
        self._reply(200, "ok")
