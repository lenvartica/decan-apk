"""Decan APK Downloader — Flask entrypoint for Vercel.

Routes:
  GET  /               status page
  POST /api/webhook    Telegram sends updates here
  GET  /api/setup?key= registers the webhook + command list (run once)
"""
import os
import traceback

from flask import Flask, jsonify, request

from bot import tg
from bot.handlers import handle_update

app = Flask(__name__)

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


@app.get("/")
@app.get("/api/webhook")
def home():
    return "Decan APK Downloader bot is running ✅"


@app.post("/api/webhook")
def webhook():
    secret = os.environ.get("WEBHOOK_SECRET")
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        return "forbidden", 403
    try:
        update = request.get_json(force=True, silent=True) or {}
        handle_update(update)
    except Exception:
        traceback.print_exc()  # shows in Vercel logs
    return "ok", 200  # always 200 so Telegram doesn't retry-spam


@app.get("/api/setup")
def setup():
    secret = os.environ.get("WEBHOOK_SECRET", "")
    if not secret or request.args.get("key") != secret:
        return jsonify({"error": "bad or missing key"}), 403
    host = request.headers.get("x-forwarded-host") or request.host
    url = f"https://{host}/api/webhook"
    hook = tg.call(
        "setWebhook",
        url=url,
        secret_token=secret,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )
    cmds = tg.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in COMMANDS])
    return jsonify({"webhook_url": url, "setWebhook": hook, "setMyCommands": cmds})


if __name__ == "__main__":  # local testing: python app.py
    app.run(port=3000, debug=True)
