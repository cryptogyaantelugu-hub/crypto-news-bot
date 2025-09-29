# send_crypto_news.py
"""
India-focused Crypto News Alerts (Scam / Hack / Govt Updates)
- Dedupe across runs (sent_ids.json, committed back to repo)
- Telugu + English style message
"""

import os, json, time, subprocess
from datetime import datetime, timezone
import requests, feedparser

# --- CONFIG ---
BOT_TOKEN = "8470241576:AAGi9s5jSfwiFTCovCHytf7x6jjbbSuJeNc" # your bot token
CHAT_ID = "7493325228" # your chat id

# Feeds: India + global security/regulatory sources
FEEDS = [
    # Crypto / global (for hacks/regulation)
    "https://cryptonews.com/rss/",
    "https://cointelegraph.com/rss",
    "https://coindesk.com/arc/outboundfeeds/rss/",
    # India business/regulation
    "https://economictimes.indiatimes.com/markets/cryptocurrency/rssfeeds/6834000.cms",
    "https://www.moneycontrol.com/rss/cryptocurrency.xml",
    "https://www.livemint.com/rss/industry/cryptocurrency",
    "https://www.business-standard.com/rss/latest.rss",
    # India regional
    "https://timesofindia.indiatimes.com/rssfeeds/-2128816011.cms",  # Hyderabad
    "https://www.deccanchronicle.com/rss_feed",                      # Deccan Chronicle (general, filter later)
    # Cybersecurity (fraud/hacks)
    "https://thehackernews.com/feeds/posts/default",
    "https://www.bleepingcomputer.com/feed/"
]

# Telugu mainstream (not official RSS → can be added later with scraping APIs)
# For now, ET + TOI + Deccan cover most fraud stories.

KEYWORDS = [
    "crypto", "cryptocurrency", "bitcoin", "ethereum", "btc", "eth",
    "scam", "fraud", "hack", "hacked", "breach", "ransomware",
    "identity", "identity theft", "PAN", "KYC", "deepfake",
    "sebi", "rbi", "regulation", "regulator", "ban", "government",
    "police", "investigation", "arrest", "telangana", "andhra", "india",
    "wallet", "exchange", "custodian"
]

MAX_ITEMS_PER_FEED = 5
MAX_TOTAL_ITEMS = 6
SENT_FILE = "sent_ids.json"

# ---------------- helpers ----------------
def load_sent_ids():
    try:
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_sent_ids(sent_set):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent_set), f, ensure_ascii=False, indent=2)

def is_relevant(title, summary, link):
    text = " ".join([title or "", summary or ""]).lower()
    return any(kw in text for kw in KEYWORDS) or any(kw in (link or "").lower() for kw in KEYWORDS)

def fetch_headlines():
    items = []
    for feed in FEEDS:
        try:
            d = feedparser.parse(feed)
            for e in d.entries[:MAX_ITEMS_PER_FEED]:
                title = e.get("title", "").strip()
                link = e.get("link", "").strip()
                summary = e.get("summary", "") or e.get("description", "")
                published = e.get("published", "") or e.get("updated", "")
                uid = e.get("id") or link or title
                items.append({
                    "id": uid,
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": published,
                    "source": d.get("feed", {}).get("title", feed)
                })
        except Exception as ex:
            print("Feed error:", feed, ex)
    return items

def build_message(selected):
    now = datetime.now(timezone.utc).astimezone().strftime("%d %b %Y %H:%M %Z")
    header = f"🔔 India Crypto Scam/Hack/Govt Alerts — {now}\n\n"
    if not selected:
        return header + "No fresh scam or govt crypto updates today."

    parts = []
    for i, it in enumerate(selected, 1):
        title = it["title"] if len(it["title"]) <= 140 else it["title"][:137] + "..."
        line = f"{i}️⃣ {title}\n👉 {it['link']}\n— {it.get('source','')}"
        parts.append(line)

    footer = (
        "\n\n⚠️ Crypto Tip: IDs guard cheyyandi 🔒, wallet addresses verify chesukondi ✅, "
        "private keys eppudu share cheyyakandi ❌.\n— @Crypto Gyaan Telugu"
    )
    return header + "\n\n".join(parts) + footer

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=20)
    r.raise_for_status()
    return r.json()

# ---------------- main ----------------
def main():
    sent = load_sent_ids()
    all_items = fetch_headlines()

    new_items = []
    for it in all_items:
        if len(new_items) >= MAX_TOTAL_ITEMS: break
        if not is_relevant(it["title"], it["summary"], it["link"]): continue
        uid = (it["link"] or it["id"] or it["title"]).strip()
        if not uid or uid in sent: continue
        new_items.append(it)
        sent.add(uid)

    if not new_items:
        print("No new relevant news to send.")
        save_sent_ids(sent)
        return

    msg = build_message(new_items)
    print("Sending message preview:\n", msg[:500])
    res = send_telegram(msg)
    print("Telegram sent:", res)
    save_sent_ids(sent)

    # Commit sent_ids.json back to repo for persistence
    try:
        subprocess.run(["git", "config", "--global", "user.email", "bot@example.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "CryptoNewsBot"], check=True)
        subprocess.run(["git", "add", SENT_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "Update sent_ids.json"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("sent_ids.json committed & pushed.")
    except Exception as e:
        print("Git commit skipped:", e)

if __name__ == "__main__":
    main()
