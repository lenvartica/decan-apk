"""Tiny Telegram Bot API wrapper (no heavy frameworks, ideal for serverless)."""
import os
import requests


def _base():
    return f"https://api.telegram.org/bot{os.environ.get('BOT_TOKEN', '')}"


def call(method, **params):
    try:
        r = requests.post(f"{_base()}/{method}", json=params, timeout=20)
        return r.json()
    except Exception as e:  # network / JSON errors
        return {"ok": False, "description": str(e)}


def send(chat_id, text, markup=None, parse_mode="HTML", **kw):
    p = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        p["parse_mode"] = parse_mode
    if markup:
        p["reply_markup"] = markup
    p.update(kw)
    return call("sendMessage", **p)


def send_photo(chat_id, photo_url, caption="", markup=None):
    p = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    return call("sendPhoto", **p)


def send_document(chat_id, filename, content, caption=""):
    try:
        r = requests.post(
            f"{_base()}/sendDocument",
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
            files={"document": (filename, content)},
            timeout=55,
        )
        return r.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}


def delete(chat_id, message_id):
    return call("deleteMessage", chat_id=chat_id, message_id=message_id)


def action(chat_id, act="typing"):
    return call("sendChatAction", chat_id=chat_id, action=act)


def answer_cb(cb_id, text=None):
    p = {"callback_query_id": cb_id}
    if text:
        p["text"] = text
    return call("answerCallbackQuery", **p)
