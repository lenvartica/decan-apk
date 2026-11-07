# Decan Bot v2.1 — change report
Apply on top of v2 (decan-apk-v2-update.zip).

New: bot/youtube.py
Changed: bot/downloaders.py (Jamendo/iTunes/TMDB removed; Internet Archive movies with posters, views, favorites, ratings),
         bot/ui.py (new YouTube screen, updated Music/Movies), bot/handlers.py, bot/util.py, app.py, .env.example, README.md
Removed features: /movieinfo (TMDB), Jamendo/iTunes music.  Env vars JAMENDO_CLIENT_ID and TMDB_API_KEY are no longer used.

Tested offline with a mocked yt-dlp / Telegram / Archive.org: search, info card, audio + video send, size limits,
bot-block message, link pasting, prompts, every menu button, Flask routes.
NOT tested against live YouTube, Telegram or Archive.org — YouTube may block Vercel's servers (see README).
