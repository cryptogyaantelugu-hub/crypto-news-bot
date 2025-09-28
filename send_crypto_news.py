# send_crypto_news.py
import os
import requests
import feedparser
from datetime import datetime, timezone

# --- CONFIG ---
BOT_TOKEN = "8470241576:AAGi9s5jSfwiFTCovCHytf7x6jjbbSuJeNc"   # your bot token
CHAT_ID   = "7493325228"                                       # your chat id

# Add RSS/news feeds you trust
FEEDS = [
    "https://cryptonews.com/rss/",                             # crypto-specific
    "https://cointelegraph.com/rss",                           # cointelegraph
    "https://coindesk.com/arc/outboundfeeds/rss/",             # coindesk
    "https://timesofindia.indiatimes.com/rssfeeds/1221656.cms" # India general
]

MAX_ITEMS = 5  # how many headlines to include

# --- helper to fetch feeds ---
def fetch_headlines():
    headlines = []
    for url in FEEDS:
        try:
            d = feedparser.parse(url)
            for entry in d.entries[:MAX_ITEMS]:
                title = entry.get("title", "No title")
                link  = entry.get("link", "")
                published = entry.get("published", "")
                headlines.append({"title": title, "link": link, "published": published})
        except Exception as e:
            print("Feed error", url, e)
    return headlines

# --- build Telugu + English message ---
def build_message(headlines):
    now = datetime.now(timezone.utc).astimezone().strftime("%d %b %Y %H:%M %Z")
    header = f"🔔 Crypto News Digest — {now}\n\n"
    if not headlines:
        return header + "No fresh headlines found."

    parts = []
    for i, h in enumerate(headlines[:MAX_ITEMS], 1):
        t = h["title"]
        l = h["link"]

        # Telugu + English style formatting
        line = f"{i}️⃣ {t} ⚡\n👉 {l}"
        parts.append(line)

    body = "\n\n".join(parts)

    footer = (
        "\n\n⚠️ Crypto Tip: "
        "KYC & IDs guard cheyyandi 🔒, wallet address verify chesukondi ✅, "
        "and never share your private keys ❌.\n"
        "— @Crypto Gyaan Telugu"
    )

    return header + body + footer

# --- send to telegram ---
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
        "parse_mode": "HTML"
    }
    r = requests.post(url, data=payload, timeout=15)
    r.raise_for_status()
    return r.json()

# --- main ---
if __name__ == "__main__":
    headlines = fetch_headlines()
    # de-duplicate titles
    unique = []
    seen = set()
    for h in headlines:
        if h["title"] not in seen:
            unique.append(h)
            seen.add(h["title"])
    msg = build_message(unique)
    print("Sending message:")
    print(msg[:1000])
    res = send_telegram(msg)
    print("Sent:", res)
