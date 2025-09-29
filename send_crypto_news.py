# send_crypto_news.py
"""
Daily Crypto News (India-focused: scams / hacks / govt updates)

Requirements:
  pip install requests feedparser

# --- CONFIG ---
BOT_TOKEN = "8470241576:AAGi9s5jSfwiFTCovCHytf7x6jjbbSuJeNc" # your bot token
CHAT_ID = "7493325228" # your chat id

Behavior:
  - Reads RSS feeds in FEEDS (India + crypto sources)
  - Filters items by KEYWORDS (crypto, scam, hack, RBI, SEBI, KYC, identity, deepfake, fraud, etc.)
  - Deduplicates using sent_ids.json (stores links/ids already sent)
  - Sends a Telugu+English mixed digest message to Telegram
"""

import os
import json
import time
from datetime import datetime, timezone
import requests
import feedparser

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

# Feeds: mix of India business / local / crypto / security feeds.
FEEDS = [
    # Crypto / global
    "https://cryptonews.com/rss/",
    "https://cointelegraph.com/rss",
    "https://coindesk.com/arc/outboundfeeds/rss/",
    "https://news.bitcoin.com/feed/",
    # Indian business / policy sections (often report govt/regulatory news)
    "https://economictimes.indiatimes.com/markets/cryptocurrency/rssfeeds/6834000.cms",  # ET crypto (if available)
    "https://www.livemint.com/rss/industry/cryptocurrency",  # Mint crypto (if available)
    "https://www.moneycontrol.com/rss/cryptocurrency.xml",
    # Times of India Telangana / India (regional) - might include local scam reports
    "https://timesofindia.indiatimes.com/rssfeeds/1221656.cms",
    "https://timesofindia.indiatimes.com/rssfeeds/-2128816011.cms",  # Hyderabad / regional (if available)
    # Cybersecurity / hacks / fraud
    "https://thehackernews.com/feeds/posts/default",
    "https://www.bleepingcomputer.com/feed/",
    # Add more as needed
]

# Keywords to match (only items containing any of these will be sent)
KEYWORDS = [
    "crypto", "cryptocurrency", "bitcoin", "ethereum", "btc", "eth",
    "scam", "fraud", "hack", "hacked", "breach", "ransomware",
    "identity", "identity theft", "PAN", "KYC", "deepfake",
    "sebi", "rbi", "regulation", "regulator", "ban", "government",
    "police", "investigation", "arrest", "telangana", "andhra", "india",
    "wallet", "exchange", "custodian"
]

MAX_ITEMS_PER_FEED = 6   # how many recent items to read per feed
MAX_TOTAL_ITEMS = 8      # how many items to include in a single digest

SENT_FILE = "sent_ids.json"  # stores sent links/ids to avoid repeat


# ---------------- helpers ----------------
def load_sent_ids():
    try:
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
    except Exception:
        return set()


def save_sent_ids(sent_set):
    try:
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(list(sent_set), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Failed to save sent ids:", e)


def is_relevant(title, summary, link):
    text = " ".join([title or "", summary or ""]).lower()
    # match any keyword
    for kw in KEYWORDS:
        if kw in text:
            return True
    # also check link text (sometimes keywords in URL)
    if any(kw in (link or "").lower() for kw in KEYWORDS):
        return True
    return False


def fetch_headlines():
    items = []
    for feed in FEEDS:
        try:
            d = feedparser.parse(feed)
            entries = d.entries[:MAX_ITEMS_PER_FEED]
            for e in entries:
                title = e.get("title", "").strip()
                link = e.get("link", "").strip()
                summary = e.get("summary", "") or e.get("description", "") or ""
                published = e.get("published", "") or e.get("updated", "")
                item_id = e.get("id") or link or title
                items.append({
                    "id": item_id,
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": published,
                    "source": d.get("feed", {}).get("title", feed)
                })
        except Exception as ex:
            print("Feed error:", feed, ex)
    # sort by published if possible, newest first (best-effort)
    def parse_date(x):
        for k in ("published_parsed", "updated_parsed"):
            v = x.get(k)
            if v:
                try:
                    return time.mktime(v)
                except Exception:
                    pass
        return 0
    items.sort(key=parse_date, reverse=True)
    return items


# ---------------- message building ----------------
def build_message(selected):
    now = datetime.now(timezone.utc).astimezone().strftime("%d %b %Y %H:%M %Z")
    header = f"🔔 Crypto (India) Alerts — {now}\n\n"

    if not selected:
        return header + "No new India crypto / scam / govt updates found."

    parts = []
    for i, it in enumerate(selected, 1):
        # Shorten title if too long
        title = it["title"] if len(it["title"]) <= 140 else it["title"][:137] + "..."
        line = f"{i}️⃣ {title}\n👉 {it['link']}\n— {it.get('source','')}"
        parts.append(line)

    body = "\n\n".join(parts)

    footer = (
        "\n\n⚠️ Tip: KYC & IDs guard cheyyandi. Wallet address verify chesukondi. "
        "Never share private keys.\n— Crypto Gyaan Telugu"
    )
    return header + body + footer


def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("TG_BOT_TOKEN or TG_CHAT_ID not set in env vars")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
        "parse_mode": "HTML"
    }
    r = requests.post(url, data=payload, timeout=20)
    # If Telegram returns 429 (rate limit) or 5xx, we may want retry logic
    r.raise_for_status()
    return r.json()


# ---------------- main flow ----------------
def main():
    sent = load_sent_ids()
    all_items = fetch_headlines()

    # Filter relevant & not-sent
    candidates = []
    for it in all_items:
        if len(candidates) >= MAX_TOTAL_ITEMS:
            break
        # simple relevance check: keywords in title/summary/link
        if not is_relevant(it["title"], it["summary"], it["link"]):
            continue
        # use link or id as unique key
        uid = (it["link"] or it["id"] or it["title"]).strip()
        if not uid:
            continue
        if uid in sent:
            continue
        candidates.append(it)
        sent.add(uid)

    # If nothing new from feeds, do nothing
    if not candidates:
        print("No new relevant items to send.")
        save_sent_ids(sent)
        return

    # Build message and send
    msg = build_message(candidates[:MAX_TOTAL_ITEMS])
    print("Sending message preview:")
    print(msg[:1000])
    res = send_telegram(msg)
    print("Telegram response:", res)

    # persist sent ids
    save_sent_ids(sent)


if __name__ == "__main__":
    main()
