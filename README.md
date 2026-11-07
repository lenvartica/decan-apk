# Decan APK Downloader — Telegram Bot (Python + Vercel)

Search and download Android APKs from Telegram, plus weather, currency converter,
URL shortener, QR codes, calculator, password generator, world time, quotes and jokes —
all behind inline menu buttons. Fully stateless (webhook-based), built for Vercel serverless.

## 1. Create the bot
1. Open **@BotFather** → `/newbot` → name it **Decan APK Downloader** → copy the token.

## 2. Deploy to Vercel
Push this folder to a GitHub repo, then **Vercel → Add New → Project → import it**
(or run `vercel --prod` with the Vercel CLI).

Add these **Environment Variables** (Project → Settings → Environment Variables):

| Name | Value |
|------|-------|
| `BOT_TOKEN` | token from BotFather |
| `WEBHOOK_SECRET` | any random string (letters, numbers, `_` `-` only) |

Redeploy after adding them.

## 3. Connect Telegram to Vercel (one time)
Open in your browser:

    https://YOUR-APP.vercel.app/api/setup?key=YOUR_WEBHOOK_SECRET

You should see `"ok": true` for both `setWebhook` and `setMyCommands`. Now message your bot and send `/start`.

## How it works
- `api/webhook.py` – receives Telegram updates
- `api/setup.py` – registers the webhook + command menu
- `bot/handlers.py` – all features and menu logic
- `bot/tg.py` – small Telegram API wrapper
- Tools that need input use Telegram's *force-reply*, so no database is needed.
- APKs come from Aptoide's public API. Files up to ~48 MB are uploaded straight into the chat;
  bigger ones get a direct download button.

## Notes
- `maxDuration` is set to 60s in `vercel.json` (needed for APK uploads). If your plan caps lower, big APKs will fall back to the download button.
- Add new features by writing a function in `bot/handlers.py` and registering it in `ACTIONS` / `COMMANDS` / the menu.
- Only download apps you're allowed to use and respect developers' licences.
