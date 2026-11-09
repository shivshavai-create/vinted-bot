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


KIDS_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg.KIDS_WORDS) + r")\b", re.I)
KIDS_SIZE_RE = re.compile(r"\b\d+\s*(?:-\s*\d+\s*)?(?:y|yr|yrs|year|years|month|months|cm)\b", re.I)


def is_banned(text, channel):
    low = text.lower()
    if BANNED_RE.search(low) or any(p in low for p in cfg.BANNED_PHRASES):
        return True
    for word in cfg.EXTRA_BANNED_BY_CHANNEL.get(channel, []):
        if re.search(r"\b" + re.escape(word) + r"\b", low):
            return True
    return False


def is_kids(title, size_title):
    size_text = size_title or ""
    if KIDS_RE.search(title + " " + size_text):
        return True
    return bool(KIDS_SIZE_RE.search(size_text))


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
    return BASE_URL + "/" + raw_url.lstrip("/")


def send_alert(title, price, url, resell, net_profit, channel):
    """Sends a simple text alert. Returns True if delivered."""
    webhook = cfg.get_webhook(channel)
    if not webhook:
        print("[WARN] No webhook secret set for " + channel)
        return False

    check = cfg.CHECKLISTS.get(channel, "Inspect tags and stitching carefully")
    lines = [
        "\U0001F525 **" + title + "**",
        "Buy: **GBP " + format(price, ".2f") + "**  |  Resell: GBP " + format(resell, ".2f")
        + "  |  Profit: **+GBP " + format(net_profit, ".2f") + "** \U0001F4B0",
        "\U0001F50D " + check,
        url,
    ]
    payload = {"username": "Deal Hunter", "content": "\n".join(lines)}

    r = None
    for attempt in range(2):
        r = requests.post(webhook, json=payload, timeout=15)
        if r.status_code in (200, 204):
            print("[SENT] #" + channel + ": " + title)
            return True
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        break
    print("[ERROR] Discord status " + str(r.status_code if r else "?") + " for #" + channel)
    return False


def run():
    seen = load_seen()
    deals = []
    queued = set()
    near_misses = []
    stats = {"checked": 0, "already_seen": 0, "kids": 0, "junk_or_size": 0,
             "price_out_of_range": 0, "low_profit": 0, "qualified": 0}

    for ch in sorted(cfg.ENABLED_CHANNELS):
        found = "yes" if cfg.get_webhook(ch) else "NO - secret missing or name mismatch"
        print("[CHECK] Webhook for " + ch + ": " + found)

    for t in cfg.TARGETS:
        if t["channel"] not in cfg.ENABLED_CHANNELS:
            continue

        query, resell, max_buy = t["query"], float(t["resell"]), float(t["max_buy"])
        min_buy = float(t.get("min_buy", cfg.MIN_BUY_PRICE))
        channel, kind = t["channel"], t.get("kind")

        print("\n[SEARCH] " + query)
        try:
            items = scraper.search({"search_text": query, "order": "newest_first"})
        except Exception as e:
            print("[WARN] Search failed: " + str(e))
            time.sleep(3)
            continue

        if not items:
            print("[WARN] 0 items (possible block or empty search)")
            time.sleep(3)
            continue

        for item in items[: cfg.ITEMS_PER_SEARCH]:
            item_id = str(field(item, "id", ""))
            if not item_id or item_id in queued:
                continue

            stats["checked"] += 1
            if item_id in seen:
                stats["already_seen"] += 1
                continue

            title = field(item, "title", "Unknown") or "Unknown"
            desc = field(item, "description", "") or ""
            text = title + " " + desc
            price = parse_price(field(item, "price"))

            if price is None:
                continue

            size_title = field(item, "size_title")

            if is_kids(title, size_title):
                stats["kids"] += 1
                seen.add(item_id)
                continue

            if is_banned(text, channel) or not size_ok(kind, size_title, text):
                stats["junk_or_size"] += 1
                seen.add(item_id)
                continue

            if not (min_buy <= price <= max_buy):
                stats["price_out_of_range"] += 1
                seen.add(item_id)
                continue

            net_profit = resell * (1 - cfg.RESELL_FEE_PCT) - price - cfg.POSTAGE_COST
            if net_profit < cfg.MIN_NET_PROFIT or net_profit < price * cfg.MIN_ROI:
                stats["low_profit"] += 1
                near_misses.append((net_profit, title, price, channel))
                seen.add(item_id)
                continue

            stats["qualified"] += 1
            queued.add(item_id)
            deals.append({
                "id": item_id, "title": title, "price": price,
                "url": full_url(field(item, "url")), "resell": resell,
                "net_profit": net_profit, "channel": channel,
            })

        time.sleep(3)

    deals.sort(key=lambda d: d["net_profit"], reverse=True)
    to_send = deals[: cfg.MAX_ALERTS_PER_RUN]

    sent = 0
    for d in to_send:
        if send_alert(d["title"], d["price"], d["url"], d["resell"], d["net_profit"], d["channel"]):
            seen.add(d["id"])
            sent += 1
        time.sleep(1)

    held = len(deals) - len(to_send)
    if held > 0:
        print("[INFO] " + str(held) + " more qualifying deals held for next run")

    save_seen(seen)

    print("\n===== SUMMARY =====")
    print("Listings checked:        " + str(stats["checked"]))
    print("Already seen (skipped):  " + str(stats["already_seen"]))
    print("Kids items blocked:      " + str(stats["kids"]))
    print("Junk word / wrong size:  " + str(stats["junk_or_size"]))
    print("Price out of range:      " + str(stats["price_out_of_range"]))
    print("Profit too low:          " + str(stats["low_profit"]))
    print("Qualified deals:         " + str(stats["qualified"]))
    print("Alerts sent to Discord:  " + str(sent))

    if near_misses:
        near_misses.sort(reverse=True)
        print("\nClosest near-misses (profit too low):")
        for profit, title, price, channel in near_misses[:5]:
            print("  GBP " + format(price, ".2f") + " '" + title[:50] + "' -> profit GBP " + format(profit, ".2f"))


if __name__ == "__main__":
    print("Hunter sweep starting...")
    run()
    print("Sweep complete.")
