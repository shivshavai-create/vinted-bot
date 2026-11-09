import json
import re
import time

import requests
from vinted_scraper import VintedScraper

import config as cfg

BASE_URL = "https://www.vinted.co.uk"
SEEN_FILE = "seen.json"
scraper = VintedScraper(BASE_URL)

BANNED_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg.BANNED_WORDS) + r")\b", re.I)


def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen)[-5000:], f)


def field(item, name, default=None):
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def parse_price(raw):
    if isinstance(raw, dict):
        raw = raw.get("amount")
    if raw is None:
        return None
    try:
        return float("".join(c for c in str(raw) if c.isdigit() or c == "."))
    except ValueError:
        return None


def is_banned(text):
    low = text.lower()
    return bool(BANNED_RE.search(low)) or any(p in low for p in cfg.BANNED_PHRASES)


def size_ok(kind, size_title, text):
    if kind is None:
        return True
    s = (size_title or "").lower() or text.lower()

    if kind == "tops":
        if "xxl" in s or "extra small" in s:
            return False
        if "extra large" in s:
            return True
        return any(t in cfg.TOPS for t in re.findall(r"[a-z]+", s))

    if kind == "bottoms":
        lo, hi = cfg.BOTTOM_RANGE
        return any(lo <= int(n) <= hi for n in re.findall(r"\d+", s))

    if kind == "shoes":
        lo, hi = cfg.SHOE_RANGE
        m = re.search(r"uk\s*(\d+(?:\.\d+)?)", s)
        nums = [float(m.group(1))] if m else [float(n) for n in re.findall(r"\d+(?:\.\d+)?", s)]
        return any(lo <= n <= hi for n in nums)

    return True


def full_url(raw_url):
    if not raw_url or not isinstance(raw_url, str) or raw_url == "0":
        return BASE_URL
    if raw_url.startswith("http"):
        return raw_url
    return f"{BASE_URL}/{raw_url.lstrip('/')}"


def send_alert(title, price, url, resell, net_profit, channel):
    """Returns True if the alert was delivered."""
    webhook = cfg.get_webhook(channel)
    if not webhook:
        print(f"⚠️ No webhook secret set for '{channel}', skipping alert.")
        return False

    payload = {
        "username": f"{channel.replace('_', ' ').title()} Hunter 🎯",
        "embeds": [{
            "title": f"🔥 STEAL: {title}"[:256],
            "url": url,
            "color": 15158332,
            "fields": [
                {"name": "Buy Price", "value": f"**£{price:.2f}**", "inline": True},
                {"name": "Conservative Resell", "value": f"**£{resell:.2f}**", "inline": True},
                {"name": "Est. Net Profit", "value": f"**+£{net_profit:.2f}** 💰", "inline": True},
                {"name": "🔍 Authenticity Checklist",
                 "value": cfg.CHECKLISTS.get(channel, "Inspect tags & stitching carefully!"),
                 "inline": False},
            ],
            "footer": {"text": "Profit is after fees + postage. Verify before buying!"},
        }],
    }

    r = None
    for attempt in range(2):
        r = requests.post(webhook, json=payload, timeout=15)
        if r.status_code == 204:
            print(f"✅ #{channel}: {title} (£{price:.2f}) -> +£{net_profit:.2f}")
            return True
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        break
    print(f"❌
