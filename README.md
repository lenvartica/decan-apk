# Decan APK Downloader — Telegram Bot (Python + Flask + Vercel)

Search and download Android APKs from Telegram, plus weather, currency converter,
URL shortener, QR codes, calculator, password generator, world time, quotes and jokes —
all behind inline menu buttons. Stateless webhook bot built for Vercel.

## Project layout (everything sits in the repo root)
```
app.py            Flask entrypoint (status page, webhook, one-time setup)
requirements.txt  flask, requests, tzdata
bot/handlers.py   all features and menus
bot/tg.py         small Telegram API wrapper
```
No `vercel.json` and no `api/` folder are needed.

## 1. Create the bot
Open **@BotFather** → `/newbot` → copy the token.

## 2. Deploy to Vercel
Push this folder's contents to the root of a GitHub repo, then import the repo in Vercel.

Add **Environment Variables** (Project → Settings → Environment Variables), then redeploy:

| Name | Value |
|------|-------|
| `BOT_TOKEN` | token from BotFather |
| `WEBHOOK_SECRET` | any random string (letters, numbers, `_` `-` only) |

## 3. Register the webhook (one time)
Open in your browser:

    https://YOUR-APP.vercel.app/api/setup?key=YOUR_WEBHOOK_SECRET

You should see `"ok": true`. Then send `/start` to your bot.

Check status any time: `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

## Notes
- APKs come from Aptoide's public API. Files up to ~48 MB are uploaded into the chat; bigger ones get a download button.
- Add features by writing a function in `bot/handlers.py` and registering it in `ACTIONS` / `COMMANDS` / the menu.
- Only download apps you're allowed to use and respect developers' licences.
