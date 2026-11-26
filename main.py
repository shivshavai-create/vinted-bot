import datetime
import json
import re
import statistics
import sys
import time
import urllib.parse

import requests
from vinted_scraper import VintedScraper

import config as cfg

BASE_URL = "https://www.vinted.co.uk"
SEEN_FILE = "seen.json"
ALERTED_FILE = "alerted.json"
STATS_FILE = "stats.json"
VALID_KINDS = {"tops", "bottoms", "shoes", "football", None}
POUND = "\u00a3"
START_TIME = time.time()

scraper = VintedScraper(BASE_URL)

KIDS_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg.KIDS_WORDS) + r")\b", re.I)
KIDS_SIZE_RE = re.compile(r"\b\d+\s*(?:-\s*\d+\s*)?(?:y|yr|yrs|year|years|month|months|cm)\b", re.I)
RED_FLAG_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg.RED_FLAG_WORDS) + r")\b", re.I)
VINTAGE_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg.WORKWEAR_VINTAGE_WORDS) + r")\b", re.I)
BUNDLE_RE = re.compile(r"(^|\W)(with|inc|incl|including|includes|plus|comes|come|and|no|without|missing|needs|excl|excluding|minus|sans|w/)(\W|$)", re.I)
NEGATION_RE = re.compile(r"\b(no|without|not|nothing|zero|never|nor|free of|free from)\b[^.!?\n]{0,25}$", re.I)

# football era detection
FOOTBALL_VINTAGE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in cfg.FOOTBALL_VINTAGE_WORDS)
    + r"|199\d|200\d|(?:9\d|0\d)[/-](?:9\d|0\d|10))\b", re.I)
FOOTBALL_MODERN_RE = re.compile(r"\b(?:20[12]\d|(?:1\d|2\d)[/-](?:1\d|2\d))\b")
FOOTBALL_SPONSOR_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg.FOOTBALL_SPONSORS) + r")\b", re.I)

# untested cameras
UNTESTED_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg.UNTESTED_WORDS) + r")\b", re.I)

# per-category compiled regexes
ACCESSORY_RES = {
    ch: re.compile(r"\b(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")\b", re.I)
    for ch, words in cfg.ACCESSORY_WORDS_BY_CHANNEL.items()
}
_banned_cache = {}


# ---------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------
def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def write_json(path, data):
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


def money(x):
    return POUND + format(x, ".2f")


def full_url(raw_url):
    if not raw_url or not isinstance(raw_url, str) or raw_url == "0":
        return BASE_URL
    if raw_url.startswith("http"):
        return raw_url
    return BASE_URL + "/" + raw_url.lstrip("/")


def get_image_url(item):
    """Main photo of the listing (full size first, then the normal one)."""
    candidates = []
    photo = field(item, "photo")
    if photo:
        for key in ("full_size_url", "url"):
            candidates.append(field(photo, key))
    photos = field(item, "photos")
    if isinstance(photos, (list, tuple)) and photos:
        for key in ("full_size_url", "url"):
            candidates.append(field(photos[0], key))
    for c in candidates:
        if isinstance(c, str) and c.startswith("http"):
            return c
    return None


def lens_link(img):
    if not img:
        return None
    return "[\U0001F50D Google Lens Check](https://lens.google.com/uploadbyurl?url=" + urllib.parse.quote(img, safe="") + ")"


def clean_title(t):
    return str(t).replace("[", "(").replace("]", ")")


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


def search_with_retry(query):
    for attempt in range(3):
        try:
            return normalize_items(scraper.search({"search_text": query, "order": "newest_first"}))
        except Exception as e:
            print("[WARN] Search attempt " + str(attempt + 1) + " failed for '" + query + "': " + str(e)[:120])
            time.sleep(4 * (attempt + 1))
    return None


# ---------------------------------------------------------------
# state: what has been checked and what has been alerted
# ---------------------------------------------------------------
def parse_day(s):
    try:
        return datetime.date.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def prune_old(mapping, today_str, days):
    today = datetime.date.fromisoformat(today_str)
    keep = {}
    for k, v in mapping.items():
        d = parse_day(v)
        if d is None:
            keep[k] = today_str
        elif (today - d).days <= days:
            keep[k] = v
    return keep


def load_state(today):
    raw_seen = read_json(SEEN_FILE)
    if isinstance(raw_seen, dict):
        seen = {str(k): str(v) for k, v in raw_seen.items()}
    elif isinstance(raw_seen, list):          # old format: a plain list of ids
        seen = {str(x): today for x in raw_seen}
    else:
        seen = {}

    alerted = {"ids": {}, "fps": {}}
    raw_al = read_json(ALERTED_FILE)
    if isinstance(raw_al, dict):
        for key in ("ids", "fps"):
            if isinstance(raw_al.get(key), dict):
                alerted[key] = {str(k): str(v) for k, v in raw_al[key].items()}

    day = read_json(STATS_FILE)
    if not isinstance(day, dict):
        day = {}

    seen = prune_old(seen, today, cfg.SEEN_RETENTION_DAYS)
    alerted["ids"] = prune_old(alerted["ids"], today, cfg.ALERTED_ID_RETENTION_DAYS)
    alerted["fps"] = prune_old(alerted["fps"], today, cfg.ALERTED_RELIST_RETENTION_DAYS)
    return seen, alerted, day


def save_state(seen, alerted, day):
    write_json(SEEN_FILE, seen)
    write_json(ALERTED_FILE, alerted)
    write_json(STATS_FILE, day)


def make_fp(seller, title):
    """Same seller + same title = the same item relisted."""
    who = seller.get("id") or seller.get("login")
    if not who:
        return None
    words = re.findall(r"\w+", title.lower())
    return str(who) + "|" + " ".join(words)[:120]


# ---------------------------------------------------------------
# config validation (clear errors instead of mystery crashes)
# ---------------------------------------------------------------
def validate_config():
    errors, warnings = [], []

    for ch in cfg.ENABLED_CHANNELS:
        dest = cfg.CATEGORY_DESTINATION.get(ch)
        if dest not in cfg.WEBHOOK_SECRETS:
            errors.append("Category '" + ch + "' points at unknown destination '" + str(dest) + "'")
        if ch not in cfg.CATEGORY_TAG or ch not in cfg.CATEGORY_COLOUR:
            errors.append("Category '" + ch + "' needs a CATEGORY_TAG and CATEGORY_COLOUR")
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
        if t["channel"] not in cfg.CATEGORY_DESTINATION:
            errors.append(label + " uses unknown category '" + str(t["channel"]) + "'")
        if t.get("kind") not in VALID_KINDS:
            errors.append(label + " has invalid kind '" + str(t.get("kind")) + "' (use tops, bottoms, shoes, football)")
        for key in ("alert_under", "postage", "ping_under"):
            if key in t and to_float(t[key]) is None:
                errors.append(label + " has a " + key + " that is not a number")
        if max_buy >= resell:
            warnings.append(label + ": max_buy is not below resell, it can never profit")

    for dest in sorted(cfg.WEBHOOK_SECRETS):
        if not cfg.get_webhook(dest):
            warnings.append("No webhook secret found for '" + dest + "' - its alerts cannot be sent")

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
def banned_re_for(channel):
    if channel not in _banned_cache:
        exempt = {w.lower() for w in cfg.BANNED_EXEMPT_BY_CHANNEL.get(channel, [])}
        words = [w for w in cfg.BANNED_WORDS if w.lower() not in exempt]
        _banned_cache[channel] = re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)
    return _banned_cache[channel]


def is_banned(text, channel):
    low = text.lower()
    if banned_re_for(channel).search(low) or any(p in low for p in cfg.BANNED_PHRASES):
        return True
    for word in cfg.EXTRA_BANNED_BY_CHANNEL.get(channel, []):
        if re.search(r"\b" + re.escape(word) + r"\b", low):
            return True
    return False


def is_title_excluded(title, channel):
    low = title.lower()
    for word in cfg.TITLE_EXCLUDE_BY_CHANNEL.get(channel, []):
        if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", low):
            return True
    return False


def is_kids(title, size_title):
    size_text = size_title or ""
    if KIDS_RE.search(title + " " + size_text):
        return True
    return bool(KIDS_SIZE_RE.search(size_text))


def is_accessory_listing(title, channel):
    """True for accessories (case, strap, laces...) listed on their own.
    Something sold WITH one ("with charger", "+ case", "no box") is fine."""
    regex = ACCESSORY_RES.get(channel)
    if regex is None:
        return False
    low = title.lower()
    for m in regex.finditer(low):
        if re.search(r"\bfor\b", low[m.end():]):
            return True
        prefix = low[max(0, m.start() - 25): m.start()]
        if BUNDLE_RE.search(prefix) or any(ch in prefix for ch in "+&,"):
            continue
        return True
    return False


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


def has_any_word(text, words):
    pattern = r"\b(" + "|".join(re.escape(w) for w in words) + r")\b"
    return bool(re.search(pattern, text, re.I))


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

    if kind == "football":
        own = (size_title or "").lower()
        if own:
            if re.search(r"\b(xxl|xxxl|2xl|3xl|xs|xxs)\b", own):
                return False
            if "extra large" in own:
                return True
            return any(t in cfg.FOOTBALL_SIZES for t in re.findall(r"[a-z]+", own))
        # no size field: only trust clear size words in the text
        return any(w in text.lower() for w in ("small", "medium", "large", " xl"))

    if kind == "bottoms":
        lo, hi = cfg.BOTTOM_RANGE
        return any(lo <= int(n) <= hi for n in re.findall(r"\d+", s))

    if kind == "shoes":
        lo, hi = cfg.SHOE_RANGE
        m = re.search(r"uk\s*(\d+(?:\.\d+)?)", s)
        if m:
            candidates = [float(m.group(1))]
        else:
            candidates = []
            for n in re.findall(r"\d+(?:\.\d+)?", s):
                v = float(n)
                if v >= 35:                 # an EU size: convert to UK (EU 43 = UK 9)
                    candidates.append(v - 34)
                elif v <= 15:
                    candidates.append(v)
        return any(lo <= c <= hi for c in candidates)

    return True


def football_era(text):
    """Returns a note if the shirt looks 90s/00s or has a classic sponsor, else None.
    Modern seasons (2010 and later) are skipped."""
    vint = FOOTBALL_VINTAGE_RE.search(text)
    modern = FOOTBALL_MODERN_RE.search(text)
    if modern and not vint:
        return None
    if vint:
        return "ERA: " + vint.group(0).lower()
    sponsor = FOOTBALL_SPONSOR_RE.search(text)
    if sponsor:
        return "CLASSIC SPONSOR: " + sponsor.group(1).lower()
    return None


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
# tiers (model recognition), rare words, sold link, offers
# ---------------------------------------------------------------
def apply_tier(channel, title, resell, max_buy, postage):
    """The most SPECIFIC matching model word wins; a tier only ever raises the price.
    Returns (resell, max_buy, tier_word_if_raised, model_name)."""
    low = title.lower()
    best, best_spec = None, -1
    for tier in cfg.MODEL_TIERS.get(channel, []):
        matched = [w for w in tier["words"] if w in low]
        if not matched:
            continue
        spec = max(len(w) for w in matched)
        if spec > best_spec or (spec == best_spec and best is not None and tier["resell"] > best["resell"]):
            best, best_spec = tier, spec
    if not best:
        return resell, max_buy, None, None
    model_name = best["words"][0]
    if float(best["resell"]) > resell:
        tier_max = best.get("max_buy") or cfg.max_buy_for(float(best["resell"]), channel, postage)
        return float(best["resell"]), max(max_buy, float(tier_max)), model_name, model_name
    return resell, max_buy, None, model_name


def find_vintage(text):
    m = VINTAGE_RE.search(text)
    return m.group(1).lower() if m else None


def find_rare(channel, text):
    low = text.lower()
    for w in cfg.RARE_WORDS.get(channel, []):
        if w in low:
            return w
    return None


def sold_link(title):
    words = re.findall(r"\w+", title)[:7]
    q = urllib.parse.quote_plus(" ".join(words))
    return "https://www.ebay.co.uk/sch/i.html?_nkw=" + q + "&LH_Sold=1&LH_Complete=1"


def suggest_offer(price):
    if not cfg.OFFER_ENABLED or price < cfg.OFFER_MIN_PRICE:
        return None
    offer = round(price * cfg.OFFER_PERCENT * 2) / 2.0
    if offer >= price:
        return None
    return max(offer, 1.0)


# ---------------------------------------------------------------
# discord
# ---------------------------------------------------------------
def post_payload(destination, payload, mentions=None):
    webhook = cfg.get_webhook(destination)
    if not webhook:
        print("[WARN] No webhook secret set for " + destination)
        return False

    body = dict(payload)
    body["username"] = "Deal Hunter"
    body["allowed_mentions"] = mentions or {"parse": []}
    r = None
    for attempt in range(3):
        try:
            r = requests.post(webhook, json=body, timeout=15)
        except requests.RequestException as e:
            print("[WARN] Discord request failed: " + str(e)[:100])
            time.sleep(2)
            continue
        if r.status_code in (200, 204):
            return True
        if r.status_code == 429:
            try:
                wait = float(r.headers.get("Retry-After", 2))
            except ValueError:
                wait = 2
            time.sleep(wait)
            continue
        break
    print("[ERROR] Discord status " + str(r.status_code if r is not None else "none") + " for #" + destination)
    return False


def post_text(destination, text):
    return post_payload(destination, {"content": text[:1900]})


def build_single_embed(d):
    flags = []
    if d.get("era_note"):
        flags.append(d["era_note"])
    if d.get("alert_under") is not None:
        flags.append("ALERT RULE: " + POUND + format(float(d["alert_under"]), ".0f")
                     + " or less, profit rules skipped")
    if d["tier_word"]:
        flags.append("MODEL: " + d["tier_word"])
    if d["rare_word"]:
        flags.append("RARE: " + d["rare_word"])
    if d["resell"] > 0 and d["price"] <= d["resell"] * 0.5:
        flags.append("UNDERPRICED: asking " + str(int(round(100 * d["price"] / d["resell"])))
                     + "% of my resell estimate")
    if d.get("market_note"):
        flags.append(d["market_note"])
    if d["misspelled"]:
        flags.append("MISSPELLED LISTING - double check it is genuine")

    lines = ["Ask: **" + money(d["price"]) + "**  |  Resell: " + money(d["resell"])]
    if d["offer"] is not None:
        lines.append("Profit at asking: **+" + money(d["net_profit"]) + "**  |  With offer ("
                     + money(d["offer"]) + "): **+" + money(d["profit_offer"]) + "** \U0001F4B0")
        lines.append("\U0001F91D " + cfg.OFFER_MESSAGE.replace("{offer}", money(d["offer"])))
    else:
        lines.append("Profit: **+" + money(d["net_profit"]) + "** \U0001F4B0")
    if flags:
        lines.append("\U0001F3AF " + "  |  ".join(flags))
    lines.append("\U0001F50D " + cfg.CHECKLISTS.get(d["channel"], "Inspect tags and stitching carefully"))
    if d["seller_login"]:
        lines.append("Seller: " + str(d["seller_login"]))

    links = ["[\U0001F6D2 Open on Vinted](" + d["url"] + ")"]
    lens = lens_link(d.get("image"))
    if lens:
        links.append(lens)
    links.append("[\U0001F4C8 eBay sold comps](" + sold_link(d["title"]) + ")")
    lines.append("  |  ".join(links))

    tag = cfg.CATEGORY_TAG.get(d["channel"], "")
    embed = {
        "title": (tag + " " + d["title"]).strip()[:250],
        "url": d["url"],
        "color": cfg.CATEGORY_COLOUR.get(d["channel"], 0x95A5A6),
        "description": "\n".join(lines)[:4000],
        "footer": {"text": "Deal Hunter"},
    }
    if d.get("image"):
        embed["image"] = {"url": d["image"]}
    return embed


def build_bundle_embeds(deals):
    deals = sorted(deals, key=lambda x: x["net_profit"], reverse=True)
    shown = deals[:cfg.BUNDLE_MAX_ITEMS_SHOWN]
    seller = deals[0]["seller_login"] or "unknown"
    total_ask = sum(x["price"] for x in deals)
    total_profit = sum(x["net_profit"] for x in deals)

    lines = [
        "Seller: **" + str(seller) + "**  |  " + str(len(deals)) + " items  |  Total ask: **"
        + money(total_ask) + "**  |  Total profit: **+" + money(total_profit) + "** \U0001F4B0",
        "\U0001F4AC Ask the seller for a bundle price before buying one by one!",
        "",
    ]
    for i, x in enumerate(shown, 1):
        tag = cfg.CATEGORY_TAG.get(x["channel"], "")
        lines.append(str(i) + ". **" + tag + "** [" + clean_title(x["title"])[:70] + "](" + x["url"] + ")")
        row = "    " + money(x["price"]) + " ask  |  resell " + money(x["resell"]) + "  |  profit **+" + money(x["net_profit"]) + "**"
        lens = lens_link(x.get("image"))
        if lens:
            row += "  |  " + lens
        lines.append(row)
    if len(deals) > len(shown):
        lines.append("+ " + str(len(deals) - len(shown)) + " more items from this seller")

    main = {
        "title": "\U0001F4E6 MULTI-ITEM WARDROBE DROP",
        "url": shown[0]["url"],
        "color": cfg.BUNDLE_COLOUR,
        "description": "\n".join(lines)[:3900],
        "footer": {"text": "Deal Hunter"},
    }
    embeds = [main]
    if shown[0].get("image"):
        main["image"] = {"url": shown[0]["image"]}
        # gallery trick: extra embeds with the SAME url merge into one photo grid
        for x in shown[1:cfg.BUNDLE_GALLERY_IMAGES]:
            if x.get("image"):
                embeds.append({"url": shown[0]["url"], "image": {"url": x["image"]}})
    return embeds


def send_single(d):
    dest = cfg.destination_for(d["channel"])
    content = ""
    mentions = None
    if d.get("ping") and dest == "mertra":
        content = cfg.PING_TEXT
        mentions = {"parse": ["everyone"]}
    ok = post_payload(dest, {"content": content, "embeds": [build_single_embed(d)]}, mentions)
    if ok:
        print("[SENT] #" + dest + ": " + d["title"])
    return ok


def send_bundle(deals):
    dests = []
    for x in deals:
        dest = cfg.destination_for(x["channel"])
        if dest not in dests:
            dests.append(dest)
    # a bundle with a Mertra / North Face item also goes to the sniper channel
    if "mertra" in dests and "sniper" not in dests:
        dests.append("sniper")

    any_ping = any(x.get("ping") for x in deals)
    embeds = build_bundle_embeds(deals)
    ok_any = False
    for dest in dests:
        content = ""
        mentions = None
        if any_ping and dest == "mertra":
            content = cfg.PING_TEXT
            mentions = {"parse": ["everyone"]}
        if post_payload(dest, {"content": content, "embeds": embeds}, mentions):
            ok_any = True
            print("[SENT] BUNDLE #" + dest + ": " + str(len(deals)) + " items from " + str(deals[0]["seller_login"]))
        time.sleep(1)
    return ok_any


# ---------------------------------------------------------------
# daily summary (stored in stats.json)
# ---------------------------------------------------------------
STAT_KEYS = ["checked", "already_alerted", "relist_blocked", "kids", "accessory_blocked",
             "brand_mismatch", "keyword_missing", "modern_skipped", "condition_flags",
             "junk_or_size", "seller_filtered", "price_out_of_range", "low_profit",
             "qualified", "sent", "bundles", "errors"]


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
        "Blocked: kids " + str(g("kids", 0)) + ", accessories " + str(g("accessory_blocked", 0))
        + ", wrong brand " + str(g("brand_mismatch", 0))
        + ", condition " + str(g("condition_flags", 0)) + ", junk/size " + str(g("junk_or_size", 0))
        + ", sellers " + str(g("seller_filtered", 0)),
        "Repeat protection: already alerted " + str(g("already_alerted", 0))
        + ", relists blocked " + str(g("relist_blocked", 0)),
        "Too expensive: " + str(g("price_out_of_range", 0)) + ", profit too low: " + str(g("low_profit", 0)),
        "Deals found: " + str(g("qualified", 0)) + ", messages sent: " + str(g("sent", 0))
        + " (wardrobe bundles: " + str(g("bundles", 0)) + ")",
    ]
    if g("keyword_missing", 0):
        lines.append("Skipped (not the wanted type): " + str(g("keyword_missing", 0)))
    if g("modern_skipped", 0):
        lines.append("Modern / wrong era skipped: " + str(g("modern_skipped", 0)))
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

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    seen, alerted, day = load_state(today)
    if day.get("day") != today:
        maybe_send_daily_summary(day)
        day = new_day_stats(today)

    print("[STATE] checked-before: " + str(len(seen)) + " | alerted ids: " + str(len(alerted["ids"]))
          + " | alerted relist fingerprints: " + str(len(alerted["fps"])))

    deals = []
    queued = set()
    queued_fps = set()
    market = {}                 # (category, model) -> {item id: price}, for the live price check
    near_misses = []
    stats = {k: 0 for k in STAT_KEYS}
    stats["already_seen"] = 0
    stats["seller_data"] = 0
    searches_total = 0
    searches_with_results = 0

    for dest in sorted(cfg.WEBHOOK_SECRETS):
        found = "yes" if cfg.get_webhook(dest) else "NO - secret missing or name mismatch"
        print("[CHECK] Webhook for " + dest + ": " + found)

    # rotate the start point every hour so, if time runs short, different searches get skipped
    targets = [t for t in cfg.TARGETS if t["channel"] in cfg.ENABLED_CHANNELS]
    if targets:
        offset = (now.hour * 11) % len(targets)
        targets = targets[offset:] + targets[:offset]

    try:
        for t in targets:
            if time.time() - START_TIME > cfg.TIME_BUDGET_SECONDS:
                print("[WARN] Time budget reached, skipping the remaining searches (state is saved).")
                break

            query = t["query"]
            base_resell, base_max = float(t["resell"]), float(t["max_buy"])
            min_buy = float(t.get("min_buy", cfg.MIN_BUY_PRICE))
            channel, kind = t["channel"], t.get("kind")
            postage = float(t.get("postage", cfg.POSTAGE_BY_CHANNEL.get(channel, cfg.POSTAGE_COST)))
            must_match = t.get("must_match")
            misspelled = bool(t.get("misspelled"))
            require_any = t.get("require_any")
            ping_under = to_float(t.get("ping_under"))
            max_items = int(t.get("items", cfg.ITEMS_PER_SEARCH))

            print("\n[SEARCH] " + query)
            searches_total += 1
            items = search_with_retry(query)

            if not items:
                print("[WARN] 0 items (possible block or empty search)")
                time.sleep(2)
                continue
            searches_with_results += 1

            for item in items[:max_items]:
                try:
                    item_id = str(field(item, "id", ""))
                    if not item_id or item_id == "None" or item_id in queued:
                        continue

                    stats["checked"] += 1
                    if item_id in alerted["ids"]:
                        stats["already_alerted"] += 1
                        continue
                    if item_id in seen:
                        seen[item_id] = today          # still listed: keep remembering it
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

                    if must_match and not any(m in title.lower() for m in must_match):
                        continue

                    # rejections below that depend on THIS search are not remembered,
                    # so another search (different size, type or limit) can still pick the listing up
                    if require_any and not has_any_word(text, require_any):
                        stats["keyword_missing"] += 1
                        continue

                    if is_kids(title, size_title):
                        stats["kids"] += 1
                        seen[item_id] = today
                        continue

                    if channel in cfg.ACCESSORY_WORDS_BY_CHANNEL and is_accessory_listing(title, channel):
                        stats["accessory_blocked"] += 1
                        seen[item_id] = today
                        continue

                    if cfg.BRAND_CHECK_ENABLED and not misspelled and not brand_ok(channel, text + " " + brand_field):
                        stats["brand_mismatch"] += 1
                        seen[item_id] = today
                        continue

                    if cfg.CONDITION_CHECK_ENABLED and find_red_flag(text):
                        stats["condition_flags"] += 1
                        seen[item_id] = today
                        continue

                    if is_banned(text, channel) or is_title_excluded(title, channel):
                        stats["junk_or_size"] += 1
                        seen[item_id] = today
                        continue

                    # football shirts: must look 90s/00s (or have a classic sponsor)
                    era_note = None
                    if channel == "football":
                        era_note = football_era(text)
                        if not era_note:
                            stats["modern_skipped"] += 1
                            seen[item_id] = today
                            continue

                    if not size_ok(kind, size_title, text):
                        stats["junk_or_size"] += 1
                        continue

                    seller = get_seller(item)
                    if seller["rep"] is not None:
                        stats["seller_data"] += 1
                    if not seller_ok(seller):
                        stats["seller_filtered"] += 1
                        seen[item_id] = today
                        continue

                    resell, max_buy, tier_word, model_name = apply_tier(channel, title, base_resell, base_max, postage)
                    if model_name:
                        market.setdefault((channel, model_name), {})[item_id] = price

                    # vintage vs modern pricing (Carhartt + Dickies only)
                    is_modern = False
                    if channel in cfg.MODERN_RESELL_FACTOR:
                        vintage_word = find_vintage(text)
                        if vintage_word:
                            era_note = "VINTAGE: " + vintage_word
                        else:
                            is_modern = True
                            factor = cfg.MODERN_RESELL_FACTOR[channel]
                            resell = resell * factor
                            max_buy = cfg.max_buy_for(resell, channel, postage)
                            era_note = "MODERN: resell cut to " + str(int(round(factor * 100))) + "%"

                    if is_modern and t.get("no_modern"):
                        stats["modern_skipped"] += 1
                        continue

                    # untested cameras: allowed, but priced lower
                    if channel in cfg.UNTESTED_RESELL_FACTOR and UNTESTED_RE.search(text):
                        factor = cfg.UNTESTED_RESELL_FACTOR[channel]
                        resell = resell * factor
                        max_buy = cfg.max_buy_for(resell, channel, postage)
                        era_note = "UNTESTED: resell cut to " + str(int(round(factor * 100))) + "%"

                    rare_word = find_rare(channel, text)

                    alert_under = t.get("alert_under")
                    if alert_under is not None:
                        max_buy = float(alert_under)
                        need_profit, need_roi = None, None
                    elif rare_word:
                        max_buy = max_buy * cfg.RARE_MAX_BUY_MULTIPLIER
                        need_profit, need_roi = cfg.RARE_MIN_NET_PROFIT, cfg.RARE_MIN_ROI
                    else:
                        need_profit = cfg.MIN_PROFIT_BY_CHANNEL.get(channel, cfg.MIN_NET_PROFIT)
                        need_roi = cfg.ROI_BY_CHANNEL.get(channel, cfg.MIN_ROI)

                    if not (min_buy <= price <= max_buy):
                        stats["price_out_of_range"] += 1
                        continue

                    net_profit = resell * (1 - cfg.RESELL_FEE_PCT) - price - postage
                    if need_profit is not None and (net_profit < need_profit or net_profit < price * need_roi):
                        stats["low_profit"] += 1
                        near_misses.append((net_profit, title, price))
                        continue

                    # repeat protection: the same seller + title was already alerted (a relist)
                    fp = make_fp(seller, title)
                    if fp and (fp in alerted["fps"] or fp in queued_fps):
                        stats["relist_blocked"] += 1
                        seen[item_id] = today
                        continue

                    offer = suggest_offer(price)
                    profit_offer = None
                    if offer is not None:
                        profit_offer = resell * (1 - cfg.RESELL_FEE_PCT) - offer - postage

                    ping = bool(ping_under is not None and price <= ping_under)

                    stats["qualified"] += 1
                    queued.add(item_id)
                    if fp:
                        queued_fps.add(fp)
                    deals.append({
                        "id": item_id, "title": title, "price": price,
                        "url": full_url(field(item, "url")), "image": get_image_url(item),
                        "resell": resell, "net_profit": net_profit, "channel": channel,
                        "tier_word": tier_word, "model": model_name, "rare_word": rare_word,
                        "misspelled": misspelled,
                        "seller_login": seller["login"], "seller_id": seller["id"],
                        "offer": offer, "profit_offer": profit_offer,
                        "era_note": era_note, "alert_under": alert_under,
                        "market_note": None, "fp": fp, "ping": ping,
                    })
                except Exception as e:
                    stats["errors"] += 1
                    print("[WARN] Skipped one listing because of an error: " + str(e)[:120])

            time.sleep(2)

        # health check: every search empty means Vinted is probably blocking us
        if searches_total > 0 and searches_with_results == 0:
            print("[ALERT] Every search returned nothing - Vinted is probably blocking this server.")
            if not day.get("block_alerted"):
                post_text(cfg.SUMMARY_CHANNEL,
                          "\u26A0\uFE0F Deal Hunter: every Vinted search returned 0 results this run. "
                          "Vinted may be blocking GitHub's servers. I will keep trying every hour.")
                day["block_alerted"] = True

        # live price check: compare each deal with the middle price of the same model seen this run
        for d in deals:
            prices = list(market.get((d["channel"], d["model"]), {}).values()) if d["model"] else []
            if len(prices) >= cfg.MARKET_MIN_LISTINGS:
                mid = statistics.median(prices)
                if mid > 0 and d["price"] <= cfg.MARKET_UNDERPRICED_RATIO * mid:
                    d["market_note"] = ("CHEAP VS VINTED: asking " + str(int(round(100 * d["price"] / mid)))
                                        + "% of the typical price for this model (" + str(len(prices)) + " listings seen)")

        # wardrobe bundles: same seller with 2+ matching items = ONE gold embed
        units = []
        by_seller = {}
        for d in deals:
            key = d["seller_id"] or d["seller_login"]
            if key:
                by_seller.setdefault(str(key), []).append(d)
            else:
                units.append({"type": "single", "deals": [d]})
        for key, group in by_seller.items():
            if len(group) >= cfg.BUNDLE_MIN_ITEMS:
                units.append({"type": "bundle", "deals": group})
            else:
                units.append({"type": "single", "deals": group})
        for u in units:
            u["profit"] = sum(x["net_profit"] for x in u["deals"])
        units.sort(key=lambda u: u["profit"], reverse=True)

        to_send = []
        per_channel = {}
        for u in units:
            if len(to_send) >= cfg.MAX_ALERTS_PER_RUN:
                break
            if u["type"] == "single":
                d = u["deals"][0]
                limit = cfg.MAX_ALERTS_BY_CHANNEL.get(d["channel"], cfg.MAX_ALERTS_PER_CHANNEL)
                if per_channel.get(d["channel"], 0) >= limit:
                    continue
                per_channel[d["channel"]] = per_channel.get(d["channel"], 0) + 1
            to_send.append(u)

        sent = 0
        for u in to_send:
            if u["type"] == "bundle":
                ok = send_bundle(u["deals"])
            else:
                ok = send_single(u["deals"][0])
            if ok:
                # remember every item FOREVER (180 days) the moment it is sent, and save straight away
                for d in u["deals"]:
                    seen[d["id"]] = today
                    alerted["ids"][d["id"]] = today
                    if d["fp"]:
                        alerted["fps"][d["fp"]] = today
                    if d["net_profit"] > day.get("best_profit", 0.0):
                        day["best_profit"] = d["net_profit"]
                        day["best_title"] = d["title"]
                save_state(seen, alerted, day)
                sent += 1
                if u["type"] == "bundle":
                    stats["bundles"] += 1
            time.sleep(1)
        stats["sent"] = sent

        held_deals = sum(len(u["deals"]) for u in units) - sum(len(u["deals"]) for u in to_send)
        if held_deals > 0:
            print("[INFO] " + str(held_deals) + " more qualifying deals held for next run")

        day["runs"] = day.get("runs", 0) + 1
        for k in STAT_KEYS:
            day[k] = day.get(k, 0) + stats[k]

        print("\n===== SUMMARY =====")
        print("Listings checked:        " + str(stats["checked"]))
        print("Already alerted (blocked): " + str(stats["already_alerted"]))
        print("Relists blocked:         " + str(stats["relist_blocked"]))
        print("Already seen (skipped):  " + str(stats["already_seen"]))
        print("Kids items blocked:      " + str(stats["kids"]))
        print("Accessories blocked:     " + str(stats["accessory_blocked"]))
        print("Wrong brand blocked:     " + str(stats["brand_mismatch"]))
        print("Not the wanted type:     " + str(stats["keyword_missing"]))
        print("Modern / wrong era:      " + str(stats["modern_skipped"]))
        print("Condition red flags:     " + str(stats["condition_flags"]))
        print("Junk word / wrong size:  " + str(stats["junk_or_size"]))
        print("Seller filtered:         " + str(stats["seller_filtered"]))
        print("Price out of range:      " + str(stats["price_out_of_range"]))
        print("Profit too low:          " + str(stats["low_profit"]))
        print("Qualified deals:         " + str(stats["qualified"]))
        print("Messages sent:           " + str(stats["sent"]) + " (bundles: " + str(stats["bundles"]) + ")")
        print("Errors (skipped items):  " + str(stats["errors"]))

        if near_misses:
            near_misses.sort(reverse=True)
            print("\nClosest near-misses (profit too low):")
            for profit, title, price in near_misses[:5]:
                print("  GBP " + format(price, ".2f") + " '" + title[:50] + "' -> profit GBP " + format(profit, ".2f"))
    finally:
        # always write state, even if something above went wrong
        save_state(seen, alerted, day)


if __name__ == "__main__":
    print("Hunter sweep starting...")
    run()
    print("Sweep complete.")
