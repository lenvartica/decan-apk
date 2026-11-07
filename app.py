"""Decan Bot — Flask entrypoint for Vercel.

  GET  /                 status page
  POST /api/webhook      Telegram updates
  GET  /api/setup?key=   register webhook + command list (run once)
  GET  /api/cron         post tech news + Decan Konnect blog/gallery to your channels
"""
import os
import traceback

from flask import Flask, jsonify, request

from bot import news, tg
from bot.handlers import handle_update

app = Flask(__name__)

COMMANDS = [
    ("menu", "Open the main menu"), ("apk", "Search & download an APK"), ("music", "YouTube music (audio)"),
    ("yt", "YouTube video downloader"), ("movie", "Movies from Internet Archive"),
    ("ig", "Instagram video downloader"), ("fb", "Facebook video downloader"),
    ("tiktok", "TikTok video downloader"), ("x", "X / Twitter video downloader"),
    ("weather", "Weather for a city"), ("currency", "Convert currency"), ("crypto", "Crypto prices"),
    ("short", "Shorten a URL"), ("qr", "Make a QR code"), ("calc", "Calculator"),
    ("password", "Password generator"), ("time", "World time"), ("dict", "Dictionary"),
    ("country", "Country info"), ("news", "Latest tech headlines"), ("blog", "Latest Decan Konnect posts"),
    ("gallery", "Latest Decan Konnect stories"), ("dice", "Roll a dice"), ("quote", "Random quote"),
    ("joke", "Random joke"), ("help", "Help"), ("about", "About this bot"),
]


@app.get("/")
@app.get("/api/webhook")
def home():
    return "Decan Bot is running ✅"


@app.post("/api/webhook")
def webhook():
    secret = os.environ.get("WEBHOOK_SECRET")
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        return "forbidden", 403
    try:
        handle_update(request.get_json(force=True, silent=True) or {})
    except Exception:
        traceback.print_exc()
    return "ok", 200


@app.get("/api/setup")
def setup():
    secret = os.environ.get("WEBHOOK_SECRET", "")
    if not secret or request.args.get("key") != secret:
        return jsonify({"error": "bad or missing key"}), 403
    host = request.headers.get("x-forwarded-host") or request.host
    url = f"https://{host}/api/webhook"
    hook = tg.call("setWebhook", url=url, secret_token=secret,
                   allowed_updates=["message", "callback_query"], drop_pending_updates=True)
    cmds = tg.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in COMMANDS])
    return jsonify({"webhook_url": url, "setWebhook": hook, "setMyCommands": cmds})


@app.get("/api/cron")
def cron():
    """Called by Vercel Cron (Authorization: Bearer CRON_SECRET) or an external pinger (?key=WEBHOOK_SECRET)."""
    secret = os.environ.get("WEBHOOK_SECRET", "")
    cron_secret = os.environ.get("CRON_SECRET", "")
    auth_ok = bool(cron_secret) and request.headers.get("Authorization") == f"Bearer {cron_secret}"
    key_ok = bool(secret) and request.args.get("key") == secret
    if not (auth_ok or key_ok):
        return jsonify({"error": "unauthorized"}), 403
    only = request.args.get("only", "all")
    try:
        return jsonify(news.run_cron(only if only in ("news", "site") else "all"))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=3000, debug=True)
