"""Tiny Telegram Bot API wrapper (no heavy frameworks, ideal for serverless)."""
import json
import os

import requests


def _base():
    return f"https://api.telegram.org/bot{os.environ.get('BOT_TOKEN', '')}"


def call(method, **params):
    try:
        r = requests.post(f"{_base()}/{method}", json=params, timeout=20)
        return r.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}


def send(chat_id, text, markup=None, parse_mode="HTML", **kw):
    p = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        p["parse_mode"] = parse_mode
    if markup:
        p["reply_markup"] = markup
    p.update(kw)
    return call("sendMessage", **p)


def edit(chat_id, message_id, text, markup=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "message_id": message_id, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        p["parse_mode"] = parse_mode
    if markup:
        p["reply_markup"] = markup
    return call("editMessageText", **p)


def send_photo(chat_id, photo_url, caption="", markup=None):
    p = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    return call("sendPhoto", **p)


def send_dice(chat_id, emoji="🎲"):
    return call("sendDice", chat_id=chat_id, emoji=emoji)


def _upload(method, field, filename, content, data, markup=None):
    data = {k: v for k, v in data.items() if v is not None}
    data["parse_mode"] = "HTML"
    if markup:
        data["reply_markup"] = json.dumps(markup)
    try:
        r = requests.post(
            f"{_base()}/{method}", data=data, files={field: (filename, content)}, timeout=120
        )
        return r.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}


def send_document(chat_id, filename, content, caption="", markup=None):
    return _upload("sendDocument", "document", filename, content,
                   {"chat_id": chat_id, "caption": caption}, markup)


def send_audio(chat_id, filename, content, caption="", title=None, performer=None, markup=None):
    return _upload("sendAudio", "audio", filename, content,
                   {"chat_id": chat_id, "caption": caption, "title": title, "performer": performer}, markup)


def send_video(chat_id, filename, content, caption="", markup=None):
    return _upload("sendVideo", "video", filename, content,
                   {"chat_id": chat_id, "caption": caption, "supports_streaming": "true"}, markup)


def delete(chat_id, message_id):
    return call("deleteMessage", chat_id=chat_id, message_id=message_id)


def action(chat_id, act="typing"):
    return call("sendChatAction", chat_id=chat_id, action=act)


def answer_cb(cb_id, text=None):
    p = {"callback_query_id": cb_id}
    if text:
        p["text"] = text
    return call("answerCallbackQuery", **p)
