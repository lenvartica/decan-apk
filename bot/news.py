"""Tech-news RSS, decankonnect.co.ke blog/gallery scraping, and channel auto-posting."""
import html
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from itertools import zip_longest

import requests

from . import store, tg
from .ui import SITE_URL, HOME, back, btn, kb
from .util import UA, esc, get_text, strip_html, truncate

FEEDS_GLOBAL = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
]
FEEDS_KENYA = [
    ("TechCabal", "https://techcabal.com/feed/"),
    ("Techweez", "https://techweez.com/feed/"),
]
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def feeds_for(kind):
    """NEWS_FEEDS env (comma list of 'Name|url' or 'url') overrides the defaults."""
    raw = os.environ.get("NEWS_FEEDS", "").strip()
    if raw:
        out = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            name, _, url = part.partition("|") if "|" in part else ("", "", part)
            if not url:
                url, name = name, ""
            out.append((name or re.sub(r"^https?://(www\.)?", "", url).split("/")[0], url))
        return out
    if kind == "kenya":
        return FEEDS_KENYA
    if kind == "global":
        return FEEDS_GLOBAL
    return FEEDS_GLOBAL + FEEDS_KENYA


# ───────────────────────── RSS parsing ─────────────────────────
def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def parse_feed(content, source):
    out = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return out
    for el in root.iter():
        if _local(el.tag) not in ("item", "entry"):
            continue
        item = {"title": "", "link": "", "summary": "", "image": "", "published": None, "source": source}
        desc_html = full_html = ""
        for ch in el:
            n, txt = _local(ch.tag), (ch.text or "").strip()
            if n == "title":
                item["title"] = strip_html(txt)
            elif n == "link":
                if txt:
                    item["link"] = txt
                elif ch.get("href") and ch.get("rel") in (None, "alternate"):
                    item["link"] = ch.get("href")
            elif n in ("description", "summary"):
                desc_html = txt
            elif n == "encoded":
                full_html = txt
            elif n == "content" and ch.get("url"):  # media:content
                u, t, med = ch.get("url"), ch.get("type", ""), ch.get("medium", "")
                if not item["image"] and (med == "image" or t.startswith("image") or u.lower().split("?")[0].endswith(IMG_EXT)):
                    item["image"] = u
            elif n == "content":  # Atom <content>
                full_html = full_html or txt
            elif n == "thumbnail" and ch.get("url") and not item["image"]:
                item["image"] = ch.get("url")
            elif n == "enclosure" and ch.get("type", "").startswith("image") and not item["image"]:
                item["image"] = ch.get("url", "")
            elif n in ("pubDate", "published", "updated", "date") and not item["published"]:
                item["published"] = _parse_date(txt)
        if not item["image"]:
            m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', full_html or desc_html)
            if m:
                item["image"] = html.unescape(m.group(1))
        item["summary"] = strip_html(desc_html or full_html)
        if item["title"] and item["link"]:
            out.append(item)
    return out


def _fetch_feed(feed):
    name, url = feed
    try:
        r = requests.get(url, timeout=10, headers=UA)
        r.raise_for_status()
        items = parse_feed(r.content, name)
    except Exception:
        items = []
    items.sort(key=lambda i: i["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return name, items


def fetch_all(feeds):
    with ThreadPoolExecutor(max_workers=6) as ex:
        return dict(ex.map(_fetch_feed, feeds))


def headlines_message(chat_id, kind="global", n=6):
    tg.action(chat_id, "typing")
    by_feed = fetch_all(feeds_for(kind))
    items = [i for lst in by_feed.values() for i in lst]
    items.sort(key=lambda i: i["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    label = "🇰🇪 Kenya tech" if kind == "kenya" else "🌍 Global tech"
    if not items:
        return tg.send(chat_id, "📰 Couldn't load headlines right now. Try again shortly.",
                       kb([back("news")]))
    lines = [f"📰 <b>{label} headlines</b>\n"]
    for i, it in enumerate(items[:n], 1):
        lines.append(f"{i}. <a href=\"{esc(it['link'])}\">{esc(truncate(it['title'], 110))}</a>\n    <i>{esc(it['source'])}</i>")
    tg.send(chat_id, "\n".join(lines), kb([back("news")]))


# ───────────────────────── decankonnect.co.ke ─────────────────────────
SITE_LINK_RE = re.compile(
    r"""href=["'](?:https?://(?:www\.)?decankonnect\.co\.ke)?/(blog|gallery)/([A-Za-z0-9_-]+)["']""", re.I)
SUPA_IMG_RE = re.compile(r"""https://[a-z0-9]+\.supabase\.co/storage/v1/object/public/[^"'\s)<>\\]+""", re.I)


def site_items():
    """Blog and gallery entries found on the site, newest-first per section, interleaved."""
    per_section = []
    for section in ("blog", "gallery"):
        seen, items = set(), []
        try:
            page = get_text(f"{SITE_URL}/{section}")
        except Exception:
            page = ""
        for sec, slug in SITE_LINK_RE.findall(page):
            if sec.lower() == section and slug not in seen:
                seen.add(slug)
                items.append({"section": section, "slug": slug, "url": f"{SITE_URL}/{section}/{slug}"})
        per_section.append(items)
    return [x for pair in zip_longest(*per_section) for x in pair if x]


def _meta_map(page):
    out = {}
    for tag in re.findall(r"<meta\s+[^>]*>", page, re.I):
        attrs = {}
        for k, v1, v2 in re.findall(r"""([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""", tag):
            attrs[k.lower()] = html.unescape(v1 or v2)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in out:
            out[key] = attrs["content"]
    return out


def site_detail(item):
    page = get_text(item["url"])
    meta = _meta_map(page)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.I | re.S)
    title = meta.get("og:title", "")
    if not title or title.strip().upper() == "DECAN KONNECT":
        title = strip_html(h1.group(1)) if h1 else ""
    if not title:
        t = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
        title = strip_html(t.group(1)) if t else item["slug"].replace("-", " ").title()
    title = re.sub(r"\s*[|–-]\s*DECAN KONNECT\s*$", "", title, flags=re.I).strip()
    desc = meta.get("og:description") or meta.get("description") or ""
    if desc.startswith("DECAN KONNECT builds useful websites"):  # generic site-wide text
        desc = ""
    if not desc:
        for p in re.findall(r"<p[^>]*>(.*?)</p>", page, re.I | re.S):
            p = strip_html(p)
            if len(p) > 60:
                desc = p
                break
    og = meta.get("og:image", "")
    supa = SUPA_IMG_RE.search(page)
    image = supa.group(0) if supa else (og if og and not og.endswith("og-image.png") else og)
    return {**item, "title": title, "desc": desc, "image": image}


def format_site_post(d):
    if d["section"] == "blog":
        icon, label, button = "📝", "Blog", "📖 Read more"
    else:
        icon, label, button = "🖼", "Photo Story", "🖼 View story"
    cap = f"{icon} <b>{esc(truncate(d['title'], 200))}</b>\n\n"
    if d["desc"]:
        cap += esc(truncate(d["desc"], 380)) + "\n\n"
    cap += f"🌐 <b>Decan Konnect</b> • {label}\n#DecanKonnect #Kenya #Technology"
    return cap, button


def format_news_post(i):
    cap = (
        f"📰 <b>{esc(truncate(i['title'], 200))}</b>\n\n"
        f"{esc(truncate(i['summary'], 300))}\n\n"
        f"📡 {esc(i['source'])}\n#TechNews #Technology"
    )
    return cap


def post_to_channel(channel, caption, image, button, url):
    markup = kb([[btn(button, url=url)]])
    if image:
        if tg.send_photo(channel, image, caption[:1020], markup).get("ok"):
            return True
    return bool(tg.send(channel, caption, markup).get("ok"))


def send_site_latest(chat_id, section, n=3):
    tg.action(chat_id, "typing")
    items = [i for i in site_items() if i["section"] == section][:n]
    if not items:
        return tg.send(chat_id, "🌐 Couldn't load the site right now. Try again shortly.", kb([back("site")]))
    for it in items:
        try:
            d = site_detail(it)
        except Exception:
            continue
        cap, button = format_site_post(d)
        if d["image"]:
            if tg.send_photo(chat_id, d["image"], cap[:1020], kb([[btn(button, url=d["url"])]])).get("ok"):
                continue
        tg.send(chat_id, cap, kb([[btn(button, url=d["url"])]]))
    tg.send(chat_id, "👆 Latest from Decan Konnect", kb([back("site")]))


# ───────────────────────── channel auto-posting (cron) ─────────────────────────
def _channels(kind):
    raw = os.environ.get(f"{kind.upper()}_CHANNEL_IDS") or os.environ.get("CHANNEL_IDS", "")
    return [c.strip() for c in raw.split(",") if c.strip()]


def _posted(channel, key):
    return store.sismember("decan:posted", f"{channel}|{key}")


def _mark(channel, key):
    store.sadd("decan:posted", f"{channel}|{key}")


def _run_news():
    chans = _channels("news")
    if not chans:
        return {"skipped": "set NEWS_CHANNEL_IDS or CHANNEL_IDS"}
    cap = int(os.environ.get("POSTS_PER_RUN", "3"))
    use_store = store.available()
    hours = 48 if use_store else float(os.environ.get("CRON_INTERVAL_HOURS", "24"))
    now = datetime.now(timezone.utc)
    by_feed = fetch_all(feeds_for("all"))
    queues = [[i for i in items if i["published"] and now - i["published"] <= timedelta(hours=hours)]
              for items in by_feed.values()]
    posted, errors = [], []
    for it in (x for group in zip_longest(*queues) for x in group if x):  # round-robin across sources
        if len(posted) >= cap:
            break
        todo = [c for c in chans if not (use_store and _posted(c, it["link"]))]
        if not todo:
            continue
        ok_any = False
        for c in todo:
            if post_to_channel(c, format_news_post(it), it["image"], "🔗 Read full story", it["link"]):
                ok_any = True
                _mark(c, it["link"])
            else:
                errors.append(f"send to {c} failed")
        if ok_any:
            posted.append(it["title"])
    return {"posted": posted, "errors": errors, "dedup": "redis" if use_store else "time-window"}


def _run_site():
    chans = _channels("site")
    if not chans:
        return {"skipped": "set SITE_CHANNEL_IDS or CHANNEL_IDS"}
    if not store.available():
        return {"skipped": "site posting needs Redis (Upstash/Vercel KV) so posts aren't repeated"}
    cap = int(os.environ.get("SITE_POSTS_PER_RUN", "2"))
    try:
        items = site_items()
    except Exception as e:
        return {"error": str(e)}
    posted, errors = [], []
    for it in items:
        if len(posted) >= cap:
            break
        key = f"site:{it['section']}/{it['slug']}"
        todo = [c for c in chans if not _posted(c, key)]
        if not todo:
            continue
        try:
            d = site_detail(it)
        except Exception:
            errors.append(f"could not read {it['url']}")
            continue
        cap_html, button = format_site_post(d)
        ok_any = False
        for c in todo:
            if post_to_channel(c, cap_html, d["image"], button, d["url"]):
                ok_any = True
                _mark(c, key)
            else:
                errors.append(f"send to {c} failed")
        if ok_any:
            posted.append(d["title"])
    return {"posted": posted, "errors": errors, "found_on_site": len(items)}


def run_cron(only="all"):
    report = {}
    if only in ("all", "news"):
        report["news"] = _run_news()
    if only in ("all", "site"):
        report["site"] = _run_site()
    return report
