# Decan Bot — Telegram (Python + Flask + Vercel)

📱 APK Store • 🎵 YouTube music & ▶️ YouTube video • 🎬 Internet Archive movies • 📸 Instagram / Facebook / TikTok / X videos •
🛠 Weather, currency, crypto, QR, passwords, dictionary, country info, world time •
🎮 Dice games, coin, 8-ball, quotes, jokes • 📰 Auto-posts tech news + Decan Konnect blog & gallery to your channels.

## Layout (repo root)
```
app.py            Flask entrypoint: webhook, setup, cron
vercel.json       daily cron → /api/cron
requirements.txt
bot/ handlers.py ui.py tools.py downloaders.py youtube.py news.py store.py tg.py util.py
```

## Deploy
1. Push to GitHub, import in Vercel. Add env vars from `.env.example` (at least `BOT_TOKEN`, `WEBHOOK_SECRET`). Redeploy.
2. Open `https://YOUR-APP.vercel.app/api/setup?key=YOUR_WEBHOOK_SECRET` once.
3. Send `/start` to the bot.

## Channel auto-posting
1. Create a Telegram channel → add the bot as **admin** (permission: post messages).
2. Set `CHANNEL_IDS=@your_channel` (and `CRON_SECRET`).
3. In Vercel → Storage / Marketplace → add **Upstash Redis** and connect it to the project (adds `KV_REST_API_*` env vars). Redis remembers what was already posted so nothing repeats — **required for blog/gallery posts**.
4. Redeploy. Test right away with `/postnow` in the bot (admins only), or open `/api/cron?key=YOUR_WEBHOOK_SECRET`.

What gets posted:
- **Tech news** — TechCrunch, The Verge, Ars Technica, BBC Technology, TechCabal, Techweez (one per source, round-robin), with image + "Read full story" button.
- **decankonnect.co.ke** — every blog post and gallery story, oldest backlog first drips out `SITE_POSTS_PER_RUN` at a time, then new ones as you publish.

Frequency: Vercel Hobby only allows **one cron per day** (set to 05:00 UTC = 08:00 Kenya). For more posts, create a free job on **cron-job.org** hitting
`https://YOUR-APP.vercel.app/api/cron?key=YOUR_WEBHOOK_SECRET` every 3–6 hours.
Use `&only=news` or `&only=site` to run one type.

## Admin commands
`/stats` (users, posts logged) • `/broadcast <text>` • `/postnow [news|site]`

## Notes
- **YouTube** (music + video): search or paste a link → card with poster, views, likes, comments → download **M4A audio** or **MP4 video** (720p max).
  No API key. Files up to ~48 MB are sent (≈ 45 min of audio, a few minutes of video); bigger ones are declined.
  Cloud servers are often blocked by YouTube — if you see the "blocking requests" message, add `YTDLP_COOKIES` (cookies.txt from a throwaway account) in Vercel, or host the bot on a VPS / home PC.
  YouTube's terms and copyright apply — only download what you have the right to save.
- **Movies:** Internet Archive only — poster, 👁 views (download count), ❤️ favorites, ⭐ rating/reviews, watch-online and download-MP4 buttons.
  (The Archive has favorites and reviews rather than "likes".)
- **Instagram/Facebook/TikTok/X:** public videos via yt-dlp. Instagram sometimes blocks servers; `YTDLP_COOKIES` can help.
- Files up to ~48 MB are sent in chat.
