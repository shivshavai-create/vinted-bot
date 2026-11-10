import datetime
import json
import re
import sys
import time
import urllib.parse

import requests
from vinted_scraper import VintedScraper

import config as cfg

BASE_URL = "https://www.vinted.co.uk"
SEEN_FILE = "seen.json"
STATS_FILE = "stats.json"
VALID_KINDS = {"tops", "bottoms", "shoes", None}

scraper = VintedScraper(BASE_URL)

BANNED_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg.BANNED_WORDS) + r")\b", re.I)
KIDS_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg.KIDS_WORDS) + r")\b", re.I)
KIDS_SIZE_RE = re.compile(r"\b\d+\s*(?:-\s*\d+\s*)?(?:y|yr|yrs|year|years|month|months|cm)\b", re.I)
RED_FLAG_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg.RED_FLAG_WORDS) + r")\b", re.I)
NEGATION_RE = re.compile(r"\b(no|without|not|nothing|zero|never|nor|free of|free from)\b[^.!?\n]{0,25}$", re.I)


# ---------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------
def load_json(path, default):
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, type(default)):
            return data
        return default
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def field(item, name, default=None):
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_price(raw):
    if raw is not None and not isinstance(raw, (str, int, float)):
        raw = field(raw, "amount")
    if raw is None:
        return None
    try:
        return float("".join(c for c in str(raw) if c.isdigit() or c == "."))
    except ValueError:
        return None


def full_url(raw_url):
    if not raw_url or not isinstance(raw_url, str) or raw_url == "0":
        return BASE_URL
    if raw_url.startswith("http"):
        return raw_url
    return BASE_URL + "/" + raw_url.lstrip("/")


def normalize_items(res):
    if res is None:
        return []
    if isinstance(res, (list, tuple)):
        return list(res)
    if isinstance(res, dict):
        inner = res.get("items", [])
        return list(inner) if isinstance(inner, (list, tuple)) else []
    inner = getattr(res, "items", None)
    if isinstance(inner, (list, tuple)):
        return list(inner)
    return []


def describe_fields(obj):
    if obj is None:
        return []
    if isinstance(obj, dict):
        return sorted(str(k) for k in obj.keys())
    try:
        return sorted(k for k in vars(obj).keys() if not k.startswith("_"))
    except TypeError:
        return sorted(k for k in dir(obj) if not k.startswith("_"))[:40]


def search_with_retry(query):
    for attempt in range(3):
        try:
            return normalize_items(scraper.search({"search_text": query, "order": "newest_first"}))
        except Exception as e:
            print("[WARN] Search attempt " + str(attempt + 1) + " failed for '" + query + "': " + str(e)[:120])
            time.sleep(4 * (attempt + 1))
    return None


# ---------------------------------------------------------------
# config validation (clear errors instead of mystery crashes)
# ---------------------------------------------------------------
def validate_config():
    errors, warnings = [], []

    for ch in cfg.ENABLED_CHANNELS:
        if ch not in cfg.WEBHOOK_SECRETS:
            errors.append("Channel '" + ch + "' is enabled but missing from WEBHOOK_SECRETS")
    if cfg.SUMMARY_CHANNEL not in cfg.WEBHOOK_SECRETS:
        errors.append("SUMMARY_CHANNEL '" + cfg.SUMMARY_CHANNEL + "' is missing from WEBHOOK_SECRETS")

    for i, t in enumerate(cfg.TARGETS):
        label = "TARGETS[" + str(i) + "] " + str(t.get("query", "?"))
        missing = [k for k in ("query", "resell", "max_buy", "channel") if k not in t]
        if missing:
            errors.append(label + " is missing: " + ", ".join(missing))
            continue
        resell, max_buy = to_float(t["resell"]), to_float(t["max_buy"])
        if resell is None or max_buy is None:
            errors.append(label + " has a resell/max_buy that is not a number")
            continue
        if t["channel"] not in cfg.WEBHOOK_SECRETS:
            errors.append(label + " uses unknown channel '" + str(t["channel"]) + "'")
        if t.get("kind") not in VALID_KINDS:
            errors.append(label + " has invalid kind '" + str(t.get("kind")) + "' (use tops, bottoms, shoes)")
        if max_buy >= resell:
            warnings.append(label + ": max_buy is not below resell, it can never profit")

    for ch in sorted(cfg.ENABLED_CHANNELS):
        if not cfg.get_webhook(ch):
            warnings.append("No webhook secret found for '" + ch + "' - its alerts cannot be sent")

    for w in warnings:
        print("[CONFIG WARNING] " + w)
    for e in errors:
        print("[CONFIG ERROR] " + e)
    if errors:
        print("Fix the errors above in config.py and run again.")
        sys.exit(1)


# ---------------------------------------------------------------
# filters
# ---------------------------------------------------------------
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


def brand_ok(channel, text):
    words = cfg.BRAND_WORDS.get(channel)
    if not words:
        return True
    low = text.lower()
    return any(w in low for w in words)


def find_red_flag(text):
    for m in RED_FLAG_RE.finditer(text):
        prefix = text[max(0, m.start() - 30): m.start()]
        if NEGATION_RE.search(prefix):
            continue
        return m.group(1).lower()
    return None


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


# ---------------------------------------------------------------
# seller info + filter
# ---------------------------------------------------------------
def get_seller(item):
    user = field(item, "user")
    return {
        "login": field(user, "login"),
        "id": field(user, "id"),
        "rep": to_float(field(user, "feedback_reputation")),
        "count": to_float(field(user, "feedback_count")),
    }


def seller_ok(seller):
    login = str(seller["login"] or "").lower()
    if login and login in [b.lower() for b in cfg.BLOCKED_SELLERS]:
        return False
    rep, count = seller["rep"], seller["count"]
    if rep is not None:
        if rep > 1.0:
            rep = rep / 5.0
        enough_reviews = (count is None) or (count >= cfg.MIN_FEEDBACK_FOR_CHECK)
        if enough_reviews and 0 < rep < cfg.MIN_SELLER_REPUTATION:
            return False
    return True


# ---------------------------------------------------------------
# tiers, rare words, sold link
# ---------------------------------------------------------------
def apply_tier(channel, title, resell, max_buy):
    low = title.lower()
    best = None
    for tier in cfg.MODEL_TIERS.get(channel, []):
        if any(w in low for w in tier["words"]):
            if best is None or tier["resell"] > best["resell"]:
                best = tier
    if best:
        return float(best["resell"]), float(best["max_buy"]), best["words"][0]
    return resell, max_buy, None


def find_rare(channel, text):
    low = text.lower()
    for w in cfg.RARE_WORDS.get(channel, []):
        if w in low:
            return w
    return None


def sold_link(title):
    words = re.findall(r"[A-Za-z0-9]+", title)[:7]
    q = urllib.parse.quote_plus(" ".join(words))
    return "https://www.ebay.co.uk/sch/i.html?_nkw=" + q + "&LH_Sold=1&LH_Complete=1"


# ---------------------------------------------------------------
# discord
# ---------------------------------------------------------------
def post_text(channel, text):
    webhook = cfg.get_webhook(channel)
    if not webhook:
        print("[WARN] No webhook secret set for " + channel)
        return False

    payload = {
        "username": "Deal Hunter",
        "content": text[:1900],
        "allowed_mentions": {"parse": []},
    }
    r = None
    for attempt in range(3):
        try:
            r = requests.post(webhook, json=payload, timeout=15)
        except requests.RequestException as e:
            print("[WARN] Discord request failed: " + str(e)[:100])
            time.sleep(2)
            continue
        if r.status_code in (200, 204):
            return True
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        break
    print("[ERROR] Discord status " + str(r.status_code if r is not None else "none") + " for #" + channel)
    return False


def send_alert(d):
    flags = []
    if d["tier_word"]:
        flags.append("MODEL: " + d["tier_word"])
    if d["rare_word"]:
        flags.append("RARE: " + d["rare_word"])
    if d["misspelled"]:
        flags.append("MISSPELLED LISTING - double check it is genuine")
    if d["seller_deals"] > 1:
        flags.append("Seller has " + str(d["seller_deals"]) + " deals this run - ask for a bundle price")

    lines = [
        "\U0001F525 **" + d["title"] + "**",
        "Buy: **GBP " + format(d["price"], ".2f") + "**  |  Resell: GBP " + format(d["resell"], ".2f")
        + "  |  Profit: **+GBP " + format(d["net_profit"], ".2f") + "** \U0001F4B0",
    ]
    if flags:
        lines.append("\U0001F3AF " + "  |  ".join(flags))
    lines.append("\U0001F50D " + cfg.CHECKLISTS.get(d["channel"], "Inspect tags and stitching carefully"))
    if d["seller_login"]:
        lines.append("Seller: " + str(d["seller_login"]))
    lines.append(d["url"])
    lines.append("Sold comps on eBay: <" + sold_link(d["title"]) + ">")

    ok = post_text(d["channel"], "\n".join(lines))
    if ok:
        print("[SENT] #" + d["channel"] + ": " + d["title"])
    return ok


# ---------------------------------------------------------------
# daily summary (stored in stats.json)
# ---------------------------------------------------------------
STAT_KEYS = ["checked", "kids", "brand_mismatch", "condition_flags", "junk_or_size",
             "seller_filtered", "price_out_of_range", "low_profit", "qualified", "sent", "errors"]


def new_day_stats(day):
    d = {"day": day, "runs": 0, "best_title": "", "best_profit": 0.0, "block_alerted": False}
    for k in STAT_KEYS:
        d[k] = 0
    return d


def maybe_send_daily_summary(day_stats):
    if not day_stats or not day_stats.get("runs"):
        return
    g = day_stats.get
    lines = [
        "\U0001F4CA **Deal Hunter daily summary for " + str(g("day")) + "**",
        "Runs: " + str(g("runs", 0)) + " (should be about 24)",
        "Listings checked: " + str(g("checked", 0)),
        "Blocked: kids " + str(g("kids", 0)) + ", wrong brand " + str(g("brand_mismatch", 0))
        + ", condition " + str(g("condition_flags", 0)) + ", junk/size " + str(g("junk_or_size", 0))
        + ", sellers " + str(g("seller_filtered", 0)),
        "Too expensive: " + str(g("price_out_of_range", 0)) + ", profit too low: " + str(g("low_profit", 0)),
        "Deals found: " + str(g("qualified", 0)) + ", alerts sent: " + str(g("sent", 0)),
    ]
    if g("errors", 0):
        lines.append("Listings that errored and were skipped: " + str(g("errors", 0)))
    if g("best_title"):
        lines.append("Best deal: " + str(g("best_title"))[:80] + " (+GBP " + format(g("best_profit", 0.0), ".2f") + ")")
    else:
        lines.append("No deals passed the filters that day. Quiet is normal!")
    post_text(cfg.SUMMARY_CHANNEL, "\n".join(lines))
    print("[INFO] Daily summary sent for " + str(g("day")))


# ---------------------------------------------------------------
# main sweep
# ---------------------------------------------------------------
def run():
    validate_config()

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    day = load_json(STATS_FILE, {})
    if day.get("day") != today:
        maybe_send_daily_summary(day)
        day = new_day_stats(today)

    seen = set(str(x) for x in load_json(SEEN_FILE, []))
    deals = []
    queued = set()
    near_misses = []
    stats = {k: 0 for k in STAT_KEYS}
    stats["already_seen"] = 0
    stats["seller_data"] = 0
    searches_total = 0
    searches_with_results = 0
    debug_printed = False

    for t in cfg.TARGETS:
        if t["channel"] not in cfg.ENABLED_CHANNELS:
            continue

        query = t["query"]
        base_resell, base_max = float(t["resell"]), float(t["max_buy"])
        min_buy = float(t.get("min_buy", cfg.MIN_BUY_PRICE))
        channel, kind = t["channel"], t.get("kind")
        must_match = t.get("must_match")
        misspelled = bool(t.get("misspelled"))

        print("\n[SEARCH] " + query)
        searches_total += 1
        items = search_with_retry(query)

        if not items:
            print("[WARN] 0 items (possible block or empty search)")
            time.sleep(3)
            continue
        searches_with_results += 1

        if not debug_printed:
            print("[DEBUG] listing fields: " + ", ".join(describe_fields(items[0])))
            print("[DEBUG] seller fields: " + ", ".join(describe_fields(field(items[0], "user"))))
            debug_printed = True

        for item in items[: cfg.ITEMS_PER_SEARCH]:
            try:
                item_id = str(field(item, "id", ""))
                if not item_id or item_id == "None" or item_id in queued:
                    continue

                stats["checked"] += 1
                if item_id in seen:
                    stats["already_seen"] += 1
                    continue

                title = str(field(item, "title", "Unknown") or "Unknown")
                desc = str(field(item, "description", "") or "")
                brand_field = str(field(item, "brand_title", "") or "")
                text = title + " " + desc
                price = parse_price(field(item, "price"))
                size_title = field(item, "size_title")
                if size_title is not None:
                    size_title = str(size_title)

                if price is None:
                    continue

                # misspelling searches: the title must really contain the misspelling
                if must_match and not any(m in title.lower() for m in must_match):
                    continue

                if is_kids(title, size_title):
                    stats["kids"] += 1
                    seen.add(item_id)
                    continue

                # NEW FILTER 1: brand check
                if cfg.BRAND_CHECK_ENABLED and not misspelled and not brand_ok(channel, text + " " + brand_field):
                    stats["brand_mismatch"] += 1
                    seen.add(item_id)
                    continue

                # NEW FILTER 2: condition red flags
                if cfg.CONDITION_CHECK_ENABLED and find_red_flag(text):
                    stats["condition_flags"] += 1
                    seen.add(item_id)
                    continue

                if is_banned(text, channel) or not size_ok(kind, size_title, text):
                    stats["junk_or_size"] += 1
                    seen.add(item_id)
                    continue

                seller = get_seller(item)
                if seller["rep"] is not None:
                    stats["seller_data"] += 1
                if not seller_ok(seller):
                    stats["seller_filtered"] += 1
                    seen.add(item_id)
                    continue

                resell, max_buy, tier_word = apply_tier(channel, title, base_resell, base_max)
                rare_word = find_rare(channel, text)

                if rare_word:
                    max_buy = max_buy * cfg.RARE_MAX_BUY_MULTIPLIER
                    need_profit, need_roi = cfg.RARE_MIN_NET_PROFIT, cfg.RARE_MIN_ROI
                else:
                    need_profit, need_roi = cfg.MIN_NET_PROFIT, cfg.MIN_ROI

                if not (min_buy <= price <= max_buy):
                    stats["price_out_of_range"] += 1
                    seen.add(item_id)
                    continue

                net_profit = resell * (1 - cfg.RESELL_FEE_PCT) - price - cfg.POSTAGE_COST
                if net_profit < need_profit or net_profit < price * need_roi:
                    stats["low_profit"] += 1
                    near_misses.append((net_profit, title, price))
                    seen.add(item_id)
                    continue

                stats["qualified"] += 1
                queued.add(item_id)
                deals.append({
                    "id": item_id, "title": title, "price": price,
                    "url": full_url(field(item, "url")), "resell": resell,
                    "net_profit": net_profit, "channel": channel,
                    "tier_word": tier_word, "rare_word": rare_word,
                    "misspelled": misspelled,
                    "seller_login": seller["login"], "seller_id": seller["id"],
                    "seller_deals": 1,
                })
            except Exception as e:
                stats["errors"] += 1
                print("[WARN] Skipped one listing because of an error: " + str(e)[:120])

        time.sleep(3)

    # health check: every search empty means Vinted is probably blocking us
    if searches_total > 0 and searches_with_results == 0:
        print("[ALERT] Every search returned nothing - Vinted is probably blocking this server.")
        if not day.get("block_alerted"):
            post_text(cfg.SUMMARY_CHANNEL,
                      "\u26A0\uFE0F Deal Hunter: every Vinted search returned 0 results this run. "
                      "Vinted may be blocking GitHub's servers. I will keep trying every hour.")
            day["block_alerted"] = True

    # bundle tip: count deals per seller
    per_seller = {}
    for d in deals:
        key = d["seller_id"] or d["seller_login"]
        if key:
            per_seller[key] = per_seller.get(key, 0) + 1
    for d in deals:
        key = d["seller_id"] or d["seller_login"]
        if key:
            d["seller_deals"] = per_seller[key]

    deals.sort(key=lambda d: d["net_profit"], reverse=True)
    to_send = deals[: cfg.MAX_ALERTS_PER_RUN]

    sent = 0
    for d in to_send:
        if send_alert(d):
            seen.add(d["id"])
            sent += 1
            if d["net_profit"] > day.get("best_profit", 0.0):
                day["best_profit"] = d["net_profit"]
                day["best_title"] = d["title"]
        time.sleep(1)
    stats["sent"] = sent

    held = len(deals) - len(to_send)
    if held > 0:
        print("[INFO] " + str(held) + " more qualifying deals held for next run")

    save_json(SEEN_FILE, sorted(seen)[-5000:])
    day["runs"] = day.get("runs", 0) + 1
    for k in STAT_KEYS:
        day[k] = day.get(k, 0) + stats[k]
    save_json(STATS_FILE, day)

    print("\n===== SUMMARY =====")
    print("Listings checked:        " + str(stats["checked"]))
    print("Already seen (skipped):  " + str(stats["already_seen"]))
    print("Kids items blocked:      " + str(stats["kids"]))
    print("Wrong brand blocked:     " + str(stats["brand_mismatch"]))
    print("Condition red flags:     " + str(stats["condition_flags"]))
    print("Junk word / wrong size:  " + str(stats["junk_or_size"]))
    print("Seller filtered:         " + str(stats["seller_filtered"]))
    print("Price out of range:      " + str(stats["price_out_of_range"]))
    print("Profit too low:          " + str(stats["low_profit"]))
    print("Qualified deals:         " + str(stats["qualified"]))
    print("Alerts sent to Discord:  " + str(stats["sent"]))
    print("Errors (skipped items):  " + str(stats["errors"]))
    print("Listings with seller rating data: " + str(stats["seller_data"])
          + " (0 means Vinted gave no ratings, so the rating filter is inactive)")

    if near_misses:
        near_misses.sort(reverse=True)
        print("\nClosest near-misses (profit too low):")
        for profit, title, price in near_misses[:5]:
            print("  GBP " + format(price, ".2f") + " '" + title[:50] + "' -> profit GBP " + format(profit, ".2f"))


if __name__ == "__main__":
    print("Hunter sweep starting...")
    run()
    print("Sweep complete.")
