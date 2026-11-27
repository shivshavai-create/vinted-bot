import datetime
import os
import sys
from zoneinfo import ZoneInfo


# ---------------------------------------------------------------
# UK TIME GATE (runs before anything else)
# GitHub's cron runs in UTC, so the UK rules are enforced here (GMT/BST safe):
#   * never run from 23:00 to 04:59 UK time (also catches delayed GitHub queues)
#   * the extra ":30" run (cron '30 17-20 * * *') only counts from 18:00 to 20:59 UK time
# Manual "Run workflow" clicks skip the check so you can test at any time.
# ---------------------------------------------------------------
def uk_time_gate():
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        print("[SCHEDULE] Manual run - quiet-hours check skipped.")
        return
    uk = datetime.datetime.now(ZoneInfo("Europe/London"))
    if uk.hour >= 23 or uk.hour < 5:
        print("[SCHEDULE] UK time is " + uk.strftime("%H:%M") + " (quiet hours 23:00-04:59). Exiting.")
        sys.exit(0)
    schedule = os.environ.get("CRON_SCHEDULE", "").split()
    if schedule and schedule[0] == "30" and not (18 <= uk.hour <= 20):
        print("[SCHEDULE] Half-hour run outside 18:00-20:59 UK time (" + uk.strftime("%H:%M") + "). Exiting.")
        sys.exit(0)
    print("[SCHEDULE] UK time " + uk.strftime("%H:%M") + " - running.")


uk_time_gate()

import io  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
import time  # noqa: E402
import urllib.parse  # noqa: E402

import requests  # noqa: E402
from vinted_scraper import VintedScraper  # noqa: E402

try:
    from PIL import Image, ImageOps
    PIL_OK = True
    RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS
except ImportError:
    PIL_OK = False
    RESAMPLE = None

import config as cfg  # noqa: E402

# UK ONLY: the scraper only ever talks to vinted.co.uk
BASE_URL = "https://www.vinted.co.uk"
UK_HOST = "vinted.co.uk"
# False = a listing is accepted when the data does not say where the seller lives
# (it is still blocked if currency/country is shown and is NOT GBP / United Kingdom).
# True = block anything that cannot be PROVEN to be UK.
UK_REQUIRE_COUNTRY_PROOF = False

# Fast Buy link. {item_id} is replaced with the listing id.
# If Vinted changes its checkout link, change it here (one line).
FAST_BUY_URL = "https://www.vinted.co.uk/transaction/buy/new?source_screen=item&transaction%5Bitem_id%5D={item_id}"

# CONDITION FILTER: only these Vinted condition labels are allowed per category
# (lower case, "contains" match). "very good" = great condition,
# "new with tags" / "new without tags" = like new. Add more categories if you want,
# e.g. "football": [...]. Categories not listed here accept any condition.
ALLOWED_CONDITIONS = {
    "shoes": ["new with tags", "new without tags", "very good"],
}
# False = if Vinted does not show the condition, the deal is still sent with a warning flag.
# True = block deals whose condition cannot be confirmed.
BLOCK_UNKNOWN_CONDITION = False
# Extra "worn out" phrases that block a listing (title + description), per category.
EXTRA_CONDITION_FLAGS = {
    "shoes": [
        "worn condition", "used condition", "well worn", "very worn", "heavily worn", "worn out",
        "scuffed", "scuffs", "beat up", "beaten", "sole wear", "heavy wear", "dirty",
        "yellowing", "yellowed", "needs cleaning", "needs a clean", "heavy creasing", "heavily creased",
    ],
}

# Used for the Tag & Era link when the listing has no brand
CATEGORY_BRAND_FALLBACK = {
    "carhartt": "Carhartt", "dickies": "Dickies", "ralph_lauren": "Ralph Lauren",
    "football": "football shirt", "cameras": "camera", "patagonia": "Patagonia",
    "shoes": "Nike", "mertra_tnf": "The North Face",
}
BRAND_DISPLAY = {
    "ralph": "Ralph Lauren", "polo": "Polo Ralph Lauren", "tnf": "The North Face",
    "northface": "The North Face", "newbalance": "New Balance", "carhart": "Carhartt",
    "dickie": "Dickies", "rrl": "RRL", "double rl": "Double RL",
}

SEEN_FILE = "seen.json"
ALERTED_FILE = "alerted.json"
STATS_FILE = "stats.json"
RECENT_FILE = "recent_sellers.json"
RECENT_SECONDS = 24 * 60 * 60
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
EXTRA_CONDITION_RES = {
    ch: re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)
    for ch, words in EXTRA_CONDITION_FLAGS.items()
}
_banned_cache = {}

UK_COUNTRY_NAMES = ("united kingdom", "great britain", "england", "scotland", "wales", "northern ireland")


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


def get_photo_urls(item):
    """All photo links we can find for the listing (best quality first)."""
    urls = []
    photos = field(item, "photos")
    if isinstance(photos, (list, tuple)):
        for p in photos:
            for key in ("full_size_url", "url"):
                v = field(p, key)
                if isinstance(v, str) and v.startswith("http"):
                    if v not in urls:
                        urls.append(v)
                    break
    if not urls:
        main = get_image_url(item)
        if main:
            urls.append(main)
    return urls


def text_field(item, *names):
    """First non-empty text value among the given field names."""
    for n in names:
        v = field(item, n)
        if v is not None and not isinstance(v, (dict, list, tuple)) and str(v).strip():
            return str(v).strip()
    return None


def nested_text(v):
    """A text value that may be a plain string or a small object with a title/name."""
    if isinstance(v, str):
        return v.strip() or None
    if v is not None and not isinstance(v, (int, float, bool, list, tuple)):
        t = field(v, "title") or field(v, "name")
        if isinstance(t, str) and t.strip():
            return t.strip()
    return None


def get_brand(item):
    for name in ("brand_title", "brand"):
        t = nested_text(field(item, name))
        if t:
            return t
    return None


def get_size(item):
    for name in ("size_title", "size"):
        t = nested_text(field(item, name))
        if t:
            return t
    return None


def get_status(item):
    for name in ("status", "condition"):
        t = nested_text(field(item, name))
        if t:
            return t
    return None


def review_stats(user):
    rep = to_float(field(user, "feedback_reputation"))
    count = to_float(field(user, "feedback_count"))
    if count is None:
        parts = [to_float(field(user, k)) for k in
                 ("positive_feedback_count", "neutral_feedback_count", "negative_feedback_count")]
        if any(p is not None for p in parts):
            count = sum(p or 0 for p in parts)
    return rep, count


def guess_brand(channel, text, use_fallback=False):
    low = text.lower()
    for w in cfg.BRAND_WORDS.get(channel, []):
        if w in low:
            return BRAND_DISPLAY.get(w, w.title())
    return CATEGORY_BRAND_FALLBACK.get(channel) if use_fallback else None


def guess_size(text):
    m = re.search(r"\buk\s*(\d+(?:\.\d+)?)\b", text, re.I)
    if m:
        return "UK " + m.group(1)
    m = re.search(r"\bsize\s*[:\-]?\s*(xxs|xs|s|m|l|xl|xxl|\d{2}(?:\.\d)?)\b", text, re.I)
    if m:
        return m.group(1).upper()
    return None


def lens_link(img):
    if not img:
        return None
    return "[\U0001F4F7 Google Lens](https://lens.google.com/uploadbyurl?url=" + urllib.parse.quote(img, safe="") + ")"


def tag_era_link(d):
    brand = (d.get("brand")
             or guess_brand(d["channel"], d["title"] + " " + str(d.get("description") or ""), use_fallback=True)
             or "vintage")
    q = urllib.parse.quote_plus(brand + " vintage neck tag guide")
    return "[\U0001F3F7\uFE0F Check Tag Era](https://www.google.com/search?tbm=isch&q=" + q + ")"


def fast_buy_url(item_id):
    return FAST_BUY_URL.replace("{item_id}", str(item_id))


def wardrobe_url(seller_id):
    return BASE_URL + "/member/" + str(seller_id) if seller_id else BASE_URL


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


def describe_fields(obj):
    """Names of the fields on a scraper object (used for the one-time [DEBUG] log lines)."""
    if obj is None:
        return []
    if isinstance(obj, dict):
        return sorted(str(k) for k in obj.keys())
    try:
        return sorted(k for k in vars(obj).keys() if not str(k).startswith("_"))
    except TypeError:
        return sorted(n for n in dir(obj) if not n.startswith("_") and not callable(getattr(obj, n, None)))


_debug_done = {"search": False, "detail": False}


# ---------------------------------------------------------------
# UK-ONLY checks (currency, link and seller country)
# ---------------------------------------------------------------
def get_currency(item):
    raw = field(item, "price")
    if raw is not None and not isinstance(raw, (str, int, float)):
        c = field(raw, "currency_code") or field(raw, "currency")
        if c:
            return str(c).strip().upper()
    c = field(item, "currency")
    if isinstance(c, str) and c.strip():
        return c.strip().upper()
    return None


def get_country(item):
    user = field(item, "user")
    for src in (user, item):
        if src is None:
            continue
        for name in ("country_iso_code", "country_code", "country_title", "country_title_local", "country"):
            v = field(src, name)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def is_uk_country(value):
    s = str(value).strip().lower()
    if len(s) <= 3:
        return s in ("gb", "uk", "gbr")
    return any(n in s for n in UK_COUNTRY_NAMES)


def listing_is_uk(item):
    """Search-stage check. Returns (ok, reason)."""
    host = urllib.parse.urlparse(full_url(field(item, "url"))).netloc.lower()
    if not host.endswith(UK_HOST):
        return False, "link is not vinted.co.uk"
    cur = get_currency(item)
    if cur is None:
        if UK_REQUIRE_COUNTRY_PROOF:
            return False, "currency unknown"
    elif cur not in ("GBP", POUND):
        return False, "currency " + cur
    country = get_country(item)
    if country is not None and not is_uk_country(country):
        return False, "country " + country
    return True, None


# ---------------------------------------------------------------
# extra listing details (fee, publish time, reviews, photos)
# ---------------------------------------------------------------
def to_unix(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        if x > 1e12:
            x = x / 1000.0
        return int(x) if x > 1e9 else None
    s = str(v).strip()
    if s.isdigit():
        return to_unix(int(s))
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


def get_created_ts(item):
    for name in ("created_at_ts", "created_at"):
        ts = to_unix(field(item, name))
        if ts:
            return ts
    photo = field(item, "photo")
    if photo:
        hi = field(photo, "high_resolution")
        if hi:
            ts = to_unix(field(hi, "timestamp"))
            if ts:
                return ts
        ts = to_unix(field(photo, "timestamp"))
        if ts:
            return ts
    return None


def get_fee_info(item, price):
    """Returns (fee, estimated). Uses Vinted's own numbers when present."""
    total = parse_price(field(item, "total_item_price"))
    if total is not None and total > price:
        return round(total - price, 2), False
    fee = parse_price(field(item, "service_fee"))
    if fee is not None and fee > 0:
        return round(fee, 2), False
    return round(0.80 + 0.04 * price, 2), True     # buyer protection estimate


def seller_avatar(item):
    user = field(item, "user")
    photo = field(user, "photo") if user is not None else None
    if photo:
        for key in ("url", "full_size_url"):
            v = field(photo, key)
            if isinstance(v, str) and v.startswith("http"):
                return v
    return None


def extract_extras(item, price):
    fee, est = get_fee_info(item, price)
    user = field(item, "user")
    rep, count = review_stats(user)
    return {
        "country": get_country(item),
        "photos": get_photo_urls(item),
        "created_ts": get_created_ts(item),
        "description": str(field(item, "description", "") or "").strip(),
        "fee": fee, "fee_estimated": est,
        "rep": rep, "rep_count": count,
        "brand": get_brand(item), "size": get_size(item), "status": get_status(item),
    }


_detail_cache = {}
_detail_state = {"fails": 0, "off_told": False}


def unwrap_item(res):
    if res is None:
        return None
    if isinstance(res, dict):
        inner = res.get("item")
        return inner if isinstance(inner, dict) else res
    inner = getattr(res, "item", None)
    if inner is not None and not callable(inner):
        return inner
    return res


def looks_like_item(res):
    return res is not None and bool(field(res, "id") or field(res, "title") or field(res, "description"))


def call_detail(item_id):
    """Tries the scraper's item lookup, then its raw API call."""
    if hasattr(scraper, "item"):
        try:
            res = unwrap_item(scraper.item(item_id))
            if looks_like_item(res):
                return res
        except Exception as e:
            print("[WARN] item() lookup failed for " + str(item_id) + ": " + str(e)[:100])
    if hasattr(scraper, "curl"):
        try:
            res = unwrap_item(scraper.curl("/api/v2/items/" + str(item_id)))
            if looks_like_item(res):
                return res
        except Exception as e:
            print("[WARN] curl lookup failed for " + str(item_id) + ": " + str(e)[:100])
    return None


def fetch_item_detail(item_id):
    """Full listing lookup (cached, with retries). Returns None if it cannot be fetched."""
    if item_id in _detail_cache:
        return _detail_cache[item_id]
    if _detail_state["fails"] >= 6:
        if not _detail_state["off_told"]:
            print("[WARN] Item lookups switched off for the rest of this run (too many failures).")
            _detail_state["off_told"] = True
        return None
    result = None
    for attempt in range(2):
        result = call_detail(item_id)
        if result is not None:
            break
        time.sleep(2 * (attempt + 1))
    if result is not None:
        _detail_state["fails"] = 0
        if not _debug_done["detail"]:
            _debug_done["detail"] = True
            print("[DEBUG] detail item fields: " + ", ".join(describe_fields(result)))
            print("[DEBUG] detail seller fields: " + ", ".join(describe_fields(field(result, "user"))))
    else:
        _detail_state["fails"] += 1
    _detail_cache[item_id] = result
    time.sleep(1)
    return result


def condition_allowed(channel, status):
    allowed = ALLOWED_CONDITIONS.get(channel)
    if not allowed:
        return True
    s = str(status or "").strip().lower()
    if not s:
        return not BLOCK_UNKNOWN_CONDITION
    return any(a in s for a in allowed)


def enrich_and_verify(d):
    """Fills gaps from the full listing, confirms UK + condition. Returns (ok, reason, kind)."""
    detail = fetch_item_detail(d["id"])
    if detail is not None:
        cur = get_currency(detail)
        if cur is not None and cur not in ("GBP", POUND):
            return False, "currency " + cur, "uk"
        ex = extract_extras(detail, d["price"])
        if d["country"] is None:
            d["country"] = ex["country"]
        if len(ex["photos"]) > len(d["photos"]):
            d["photos"] = ex["photos"]
        if d["created_ts"] is None:
            d["created_ts"] = ex["created_ts"]
        if not d["description"]:
            d["description"] = ex["description"]
        if d["fee_estimated"] and not ex["fee_estimated"]:
            d["fee"], d["fee_estimated"] = ex["fee"], False
        if d["rep"] is None:
            d["rep"] = ex["rep"]
        if d["rep_count"] is None:
            d["rep_count"] = ex["rep_count"]
        if not d.get("brand"):
            d["brand"] = ex["brand"]
        if not d.get("size"):
            d["size"] = ex["size"]
        if not d.get("status"):
            d["status"] = ex["status"]
        if not d.get("image") and d["photos"]:
            d["image"] = d["photos"][0]

    if d["country"] is not None and not is_uk_country(d["country"]):
        return False, "country " + str(d["country"]), "uk"
    if d["country"] is None and UK_REQUIRE_COUNTRY_PROOF:
        return False, "seller country unknown", "uk"

    ch = d["channel"]
    if ch in ALLOWED_CONDITIONS:
        if d.get("status"):
            if not condition_allowed(ch, d["status"]):
                return False, "condition '" + str(d["status"]) + "'", "condition"
        elif BLOCK_UNKNOWN_CONDITION:
            return False, "condition not shown", "condition"
    return True, None, None


# ---------------------------------------------------------------
# 3-photo collage (Pillow): 1 big photo left, 2 small stacked photos right
# ---------------------------------------------------------------
def download_image(url):
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and r.content:
            return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print("[WARN] Photo download failed: " + str(e)[:80])
    return None


def build_collage(urls):
    """Returns PNG bytes, or None (then the embed just uses the main photo link)."""
    if not PIL_OK or len(urls) < 2:
        return None
    imgs = []
    for u in urls[:3]:
        im = download_image(u)
        if im is not None:
            imgs.append(im)
    if len(imgs) < 2:
        return None
    try:
        W, H, GAP = 1200, 800, 6
        left_w = 796
        right_x = left_w + GAP
        right_w = W - right_x
        canvas = Image.new("RGB", (W, H), (32, 34, 37))
        canvas.paste(ImageOps.fit(imgs[0], (left_w, H), RESAMPLE), (0, 0))
        if len(imgs) == 2:
            canvas.paste(ImageOps.fit(imgs[1], (right_w, H), RESAMPLE), (right_x, 0))
        else:
            half = (H - GAP) // 2
            canvas.paste(ImageOps.fit(imgs[1], (right_w, half), RESAMPLE), (right_x, 0))
            canvas.paste(ImageOps.fit(imgs[2], (right_w, half), RESAMPLE), (right_x, half + GAP))
        buf = io.BytesIO()
        canvas.save(buf, "PNG")
        return buf.getvalue()
    except Exception as e:
        print("[WARN] Collage failed: " + str(e)[:100])
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


def load_recent():
    """seller id -> Unix time of their last alert. Anything older than 24 hours is dropped."""
    raw = read_json(RECENT_FILE)
    out = {}
    now = time.time()
    if isinstance(raw, dict):
        for k, v in raw.items():
            ts = to_float(v)
            if ts is not None and now - ts < RECENT_SECONDS:
                out[str(k)] = ts
    return out


def save_state(seen, alerted, day, recent):
    now = time.time()
    for k in [k for k, v in recent.items() if now - v >= RECENT_SECONDS]:
        del recent[k]
    write_json(SEEN_FILE, seen)
    write_json(ALERTED_FILE, alerted)
    write_json(STATS_FILE, day)
    write_json(RECENT_FILE, recent)


def make_fp(seller, title):
    """Same seller + same title = the same item relisted."""
    who = seller.get("id") or seller.get("login")
    if not who:
        return None
    words = re.findall(r"\w+", title.lower())
    return str(who) + "|" + " ".join(words)[:120]


def seller_key(d):
    return str(d.get("seller_id") or d.get("seller_login") or "")


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
    for src, extra in cfg.BUNDLE_ALSO_POST_TO.items():
        if src not in cfg.WEBHOOK_SECRETS or extra not in cfg.WEBHOOK_SECRETS:
            errors.append("BUNDLE_ALSO_POST_TO has an unknown channel: " + str(src) + " -> " + str(extra))

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

    if not PIL_OK:
        warnings.append("Pillow is not installed - collages are switched off (single photo used instead)")

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


def find_extra_condition_flag(text, channel):
    regex = EXTRA_CONDITION_RES.get(channel)
    if regex is None:
        return None
    for m in regex.finditer(text):
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
# visual helpers
# ---------------------------------------------------------------
HOT_BANNER = "\U0001F6A8 HOT STREAK SELLER \u2014 CHECK WARDROBE NOW"


def deal_roi(d):
    return (d["net_profit"] / d["price"]) if d["price"] > 0 else 0.0


def tier_label(profit):
    for threshold, label in cfg.PROFIT_TIERS:
        if profit >= threshold:
            return label
    return cfg.PROFIT_TIERS[-1][1]


def score_stars(roi):
    roi = max(roi, 0.0)
    if roi >= 3.0:
        n = 5
    elif roi >= 2.0:
        n = 4
    elif roi >= 1.2:
        n = 3
    elif roi >= 0.8:
        n = 2
    else:
        n = 1
    return "\u2B50" * n + "\u2606" * (5 - n)


def roi_bar(roi):
    roi = max(roi, 0.0)
    blocks = min(10, int(round(roi / 3.0 * 10)))
    return "\u25B0" * blocks + "\u25B1" * (10 - blocks) + "  " + str(int(round(roi * 100))) + "%"


def mk_field(name, value, inline=True):
    return {"name": name[:256], "value": (str(value) or "-")[:1024], "inline": inline}


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def reviews_text(rep, count):
    if rep is None and not count:
        return "No reviews yet"
    r = rep if rep is not None else 0.0
    if r > 1.0:
        r = r / 5.0
    n = max(0, min(5, int(round(r * 5))))
    return "\u2B50" * n + "\u2606" * (5 - n) + " (" + str(int(count or 0)) + ")"


def short_desc(text):
    t = " ".join(str(text or "").split())
    if not t:
        return "No description provided"
    return t[:150] + ("..." if len(t) > 150 else "")


# ---------------------------------------------------------------
# discord
# ---------------------------------------------------------------
def post_payload(destination, payload, mentions=None, username=None, avatar=None, files=None):
    webhook = cfg.get_webhook(destination)
    if not webhook:
        print("[WARN] No webhook secret set for " + destination)
        return False

    body = dict(payload)
    body["username"] = (username or cfg.DEFAULT_BOT_NAME)[:80]
    if avatar:
        body["avatar_url"] = avatar
    body["allowed_mentions"] = mentions or {"parse": []}
    r = None
    for attempt in range(3):
        try:
            if files:
                multipart = {"files[" + str(i) + "]": (name, data, "image/png")
                             for i, (name, data) in enumerate(files)}
                r = requests.post(webhook, data={"payload_json": json.dumps(body)},
                                  files=multipart, timeout=40)
            else:
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


def build_single_embed(d, collage_ok):
    roi = deal_roi(d)
    tag = cfg.CATEGORY_TAG.get(d["channel"], "")
    total = d["price"] + d["fee"]
    est = "~" if d["fee_estimated"] else ""
    title_text = d["title"] + " " + str(d.get("description") or "")

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
    if d.get("ping"):
        flags.append("BARGAIN PING")
    if d["channel"] in ALLOWED_CONDITIONS and not d.get("status"):
        flags.append("CONDITION NOT SHOWN - check the photos")

    desc_lines = []
    if d.get("hot"):
        desc_lines.append("**" + HOT_BANNER + "**")
    desc_lines.append("**" + tier_label(d["net_profit"]) + "**  \u00B7  " + score_stars(roi) + "  deal score")
    desc_lines.append(short_desc(d.get("description")))

    published = "<t:" + str(d["created_ts"]) + ":R>" if d.get("created_ts") else "Unknown"

    brand_text = d.get("brand")
    if not brand_text:
        g = guess_brand(d["channel"], title_text)
        brand_text = (g + " (from title)") if g else "Not specified"
    size_text = d.get("size")
    if not size_text:
        g = guess_size(title_text)
        size_text = (g + " (from title)") if g else "Not specified"

    # the 6-field grid: two rows of three
    fields = [
        mk_field("\U0001F4B0 Price", format(d["price"], ".2f") + " " + POUND
                 + " (+ " + est + format(d["fee"], ".2f") + " " + POUND + ")"),
        mk_field("\U0001F3F7\uFE0F Brand", brand_text),
        mk_field("\U0001F4CF Size", size_text),
        mk_field("\u2728 Condition", d.get("status") or "Not specified"),
        mk_field("\u23F1\uFE0F Published", published),
        mk_field("\U0001F31F Reviews", reviews_text(d.get("rep"), d.get("rep_count"))),
    ]

    links = [
        "**[\u26A1 Fast Buy](" + fast_buy_url(d["id"]) + ")**",
        "[\U0001F50D View](" + d["url"] + ")",
        "[\U0001F464 Seller Wardrobe](" + wardrobe_url(d.get("seller_id")) + ")",
    ]
    lens = lens_link(d.get("image"))
    if lens:
        links.append(lens)
    links.append(tag_era_link(d))
    links.append("[\U0001F4C8 eBay Sold](" + sold_link(d["title"]) + ")")
    fields.append(mk_field("\U0001F517 Links", "  \u00B7  ".join(links), False))

    profit_lines = [roi_bar(roi),
                    "Resell " + money(d["resell"]) + "  \u00B7  Profit **+" + money(d["net_profit"]) + "**"]
    if d["offer"] is not None:
        profit_lines.append("\U0001F91D Offer " + money(d["offer"]) + " \u2192 profit +" + money(d["profit_offer"]))
        profit_lines.append("```" + cfg.OFFER_MESSAGE.replace("{offer}", money(d["offer"])) + "```")
    if flags:
        profit_lines.append("\U0001F3AF " + "  \u00B7  ".join(flags))
    fields.append(mk_field("\U0001F4B9 Profit check", "\n".join(profit_lines), False))

    embed = {
        "title": ("\U0001F1EC\U0001F1E7 " + d["title"][:200] + " | " + format(total, ".2f") + " " + POUND)[:250],
        "url": d["url"],
        "color": cfg.CATEGORY_COLOUR.get(d["channel"], 0x95A5A6),
        "description": "\n".join(desc_lines)[:1000],
        "fields": fields,
        "footer": {"text": (tag + "  \u00B7  " + cfg.CHECKLISTS.get(d["channel"], "Inspect tags and stitching carefully"))[:300]},
    }
    author = {"name": str(d.get("seller_login") or "Unknown seller")[:200]}
    if d.get("seller_id"):
        author["url"] = wardrobe_url(d["seller_id"])
    if d.get("avatar"):
        author["icon_url"] = d["avatar"]
    embed["author"] = author

    if collage_ok:
        embed["image"] = {"url": "attachment://collage.png"}
    elif d.get("image"):
        embed["image"] = {"url": d["image"]}
    return embed


def build_bundle_embeds(deals):
    deals = sorted(deals, key=lambda x: x["net_profit"], reverse=True)
    shown = deals[:cfg.BUNDLE_MAX_ITEMS_SHOWN]
    seller = deals[0]["seller_login"] or "unknown"
    total_ask = sum(x["price"] for x in deals)
    total_profit = sum(x["net_profit"] for x in deals)
    total_resell = sum(x["resell"] for x in deals)

    fields = [
        mk_field("\U0001F4B7 Total ask", money(total_ask)),
        mk_field("\U0001F3F7\uFE0F Total resell", money(total_resell)),
        mk_field("\U0001F4B0 Total profit", "+" + money(total_profit)),
    ]
    for i, x in enumerate(shown, 1):
        tag = cfg.CATEGORY_TAG.get(x["channel"], "")
        value = (money(x["price"]) + " ask  \u00B7  resell " + money(x["resell"])
                 + "  \u00B7  profit **+" + money(x["net_profit"]) + "**\n"
                 + "**[\u26A1 Fast Buy](" + fast_buy_url(x["id"]) + ")**  \u00B7  [\U0001F50D View](" + x["url"] + ")")
        lens = lens_link(x.get("image"))
        if lens:
            value += "  \u00B7  " + lens
        fields.append(mk_field(str(i) + ". " + tag + " " + clean_title(x["title"])[:200], value, False))
    if len(deals) > len(shown):
        fields.append(mk_field("\u2795 More", str(len(deals) - len(shown)) + " more items from this seller", False))

    main = {
        "title": "\U0001F4E6 MULTI-ITEM WARDROBE DROP",
        "url": shown[0]["url"],
        "color": cfg.BUNDLE_COLOUR,
        "description": "**" + HOT_BANNER + "**\n**" + str(len(deals)) + " matching items** from **" + str(seller)
                       + "**\n\U0001F4AC Ask for a bundle price before buying one by one!",
        "fields": fields,
        "footer": {"text": "Deal Hunter \U0001F4E6 bundle"},
        "timestamp": now_iso(),
    }
    author = {"name": str(seller)[:200]}
    if deals[0].get("seller_id"):
        author["url"] = wardrobe_url(deals[0]["seller_id"])
    main["author"] = author

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
    content_parts = []
    everyone = False
    roles = []
    if d.get("ping") and dest == "mertra":
        content_parts.append(cfg.PING_TEXT)
        everyone = True
    role_id = cfg.ROLE_PING_IDS.get(d["channel"])
    if role_id:
        content_parts.append("<@&" + str(role_id) + ">")
        roles.append(str(role_id))
    mentions = {"parse": ["everyone"] if everyone else []}
    if roles:
        mentions["roles"] = roles

    collage = build_collage(d.get("photos") or [])
    files = [("collage.png", collage)] if collage else None
    ok = post_payload(dest,
                      {"content": " ".join(content_parts), "embeds": [build_single_embed(d, bool(collage))]},
                      mentions,
                      username=cfg.CATEGORY_BOT_NAME.get(d["channel"]),
                      avatar=cfg.CATEGORY_AVATAR.get(d["channel"]),
                      files=files)
    if not ok and files:
        # retry once without the collage so a big upload can never lose the alert
        ok = post_payload(dest,
                          {"content": " ".join(content_parts), "embeds": [build_single_embed(d, False)]},
                          mentions,
                          username=cfg.CATEGORY_BOT_NAME.get(d["channel"]),
                          avatar=cfg.CATEGORY_AVATAR.get(d["channel"]))
    if ok:
        print("[SENT] #" + dest + ": " + d["title"])
    return ok


def send_bundle(deals):
    dests = []
    for x in deals:
        dest = cfg.destination_for(x["channel"])
        if dest not in dests:
            dests.append(dest)
    for dest in list(dests):
        extra = cfg.BUNDLE_ALSO_POST_TO.get(dest)
        if extra and extra not in dests:
            dests.append(extra)

    embeds = build_bundle_embeds(deals)
    any_ping = any(x.get("ping") for x in deals)
    ok_any = False
    for dest in dests:
        content_parts = []
        everyone = False
        roles = []
        if any_ping and dest == "mertra":
            content_parts.append(cfg.PING_TEXT)
            everyone = True
        for x in deals:
            rid = cfg.ROLE_PING_IDS.get(x["channel"])
            if rid and cfg.destination_for(x["channel"]) == dest and str(rid) not in roles:
                roles.append(str(rid))
        for rid in roles:
            content_parts.append("<@&" + rid + ">")
        mentions = {"parse": ["everyone"] if everyone else []}
        if roles:
            mentions["roles"] = roles
        if post_payload(dest, {"content": " ".join(content_parts), "embeds": embeds}, mentions,
                        username=cfg.BUNDLE_BOT_NAME):
            ok_any = True
            print("[SENT] BUNDLE #" + dest + ": " + str(len(deals)) + " items from " + str(deals[0]["seller_login"]))
        time.sleep(1)
    return ok_any


# ---------------------------------------------------------------
# daily summary (stored in stats.json) with the top 3 deals and photos
# ---------------------------------------------------------------
STAT_KEYS = ["checked", "already_alerted", "relist_blocked", "kids", "accessory_blocked",
             "brand_mismatch", "keyword_missing", "modern_skipped", "condition_flags",
             "bad_condition", "junk_or_size", "seller_filtered", "non_uk", "price_out_of_range",
             "low_profit", "qualified", "sent", "bundles", "errors"]


def new_day_stats(day):
    d = {"day": day, "runs": 0, "best_title": "", "best_profit": 0.0, "block_alerted": False, "top": []}
    for k in STAT_KEYS:
        d[k] = 0
    return d


def remember_top(day, d):
    """Keep the 3 best deals of the day (with photo) for the daily summary."""
    top = day.get("top")
    if not isinstance(top, list):
        top = []
    top.append({
        "title": d["title"], "profit": round(d["net_profit"], 2), "price": d["price"],
        "url": d["url"], "image": d.get("image"), "tag": cfg.CATEGORY_TAG.get(d["channel"], ""),
    })
    top.sort(key=lambda x: x.get("profit", 0), reverse=True)
    day["top"] = top[:3]


def maybe_send_daily_summary(day_stats):
    if not day_stats or not day_stats.get("runs"):
        return
    g = day_stats.get
    lines = [
        "Runs: **" + str(g("runs", 0)) + "**",
        "Listings checked: **" + str(g("checked", 0)) + "**",
        "Blocked: kids " + str(g("kids", 0)) + ", accessories " + str(g("accessory_blocked", 0))
        + ", wrong brand " + str(g("brand_mismatch", 0))
        + ", condition " + str(g("condition_flags", 0)) + ", condition filter " + str(g("bad_condition", 0))
        + ", junk/size " + str(g("junk_or_size", 0))
        + ", sellers " + str(g("seller_filtered", 0)) + ", non-UK " + str(g("non_uk", 0)),
        "Repeat protection: already alerted " + str(g("already_alerted", 0))
        + ", relists blocked " + str(g("relist_blocked", 0)),
        "Too expensive: " + str(g("price_out_of_range", 0)) + ", profit too low: " + str(g("low_profit", 0)),
        "Deals found: **" + str(g("qualified", 0)) + "**, messages sent: **" + str(g("sent", 0))
        + "** (wardrobe bundles: " + str(g("bundles", 0)) + ")",
    ]
    if g("keyword_missing", 0):
        lines.append("Skipped (not the wanted type): " + str(g("keyword_missing", 0)))
    if g("modern_skipped", 0):
        lines.append("Modern / wrong era skipped: " + str(g("modern_skipped", 0)))
    if g("errors", 0):
        lines.append("Listings that errored and were skipped: " + str(g("errors", 0)))
    if not g("best_title"):
        lines.append("No deals passed the filters that day. Quiet is normal!")

    embed = {
        "title": "\U0001F4CA Deal Hunter daily summary - " + str(g("day")),
        "color": 0x5865F2,
        "description": "\n".join(lines)[:3800],
        "footer": {"text": "Deal Hunter"},
        "timestamp": now_iso(),
    }
    embeds = [embed]
    top = g("top", [])
    if isinstance(top, list) and top:
        medals = ["\U0001F947", "\U0001F948", "\U0001F949"]
        fields = []
        for i, t in enumerate(top[:3]):
            fields.append(mk_field(
                medals[i] + " " + str(t.get("tag", "")) + " " + clean_title(t.get("title", ""))[:200],
                "+" + money(float(t.get("profit", 0))) + " profit  \u00B7  ask " + money(float(t.get("price", 0)))
                + "  \u00B7  [Open](" + str(t.get("url", BASE_URL)) + ")", False))
        embed["fields"] = fields
        first = top[0]
        if first.get("image"):
            embed["url"] = first.get("url", BASE_URL)
            embed["image"] = {"url": first["image"]}
            for t in top[1:3]:
                if t.get("image"):
                    embeds.append({"url": first.get("url", BASE_URL), "image": {"url": t["image"]}})
    post_payload(cfg.SUMMARY_CHANNEL, {"embeds": embeds}, username="Deal Hunter \U0001F4CA")
    print("[INFO] Daily summary sent for " + str(g("day")))


# ---------------------------------------------------------------
# main sweep
# ---------------------------------------------------------------
def run():
    validate_config()

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    seen, alerted, day = load_state(today)
    recent = load_recent()
    if day.get("day") != today:
        maybe_send_daily_summary(day)
        day = new_day_stats(today)

    print("[UK ONLY] searching " + BASE_URL + " | GBP listings and UK sellers only")
    print("[STATE] checked-before: " + str(len(seen)) + " | alerted ids: " + str(len(alerted["ids"]))
          + " | alerted relist fingerprints: " + str(len(alerted["fps"]))
          + " | sellers alerted in last 24h: " + str(len(recent)))

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
        offset = (now.hour * 17) % len(targets)
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

            if not _debug_done["search"]:
                _debug_done["search"] = True
                print("[DEBUG] search item fields: " + ", ".join(describe_fields(items[0])))
                print("[DEBUG] search seller fields: " + ", ".join(describe_fields(field(items[0], "user"))))

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

                    # UK ONLY: GBP price, a vinted.co.uk link and (when shown) a UK seller
                    uk_ok, uk_reason = listing_is_uk(item)
                    if not uk_ok:
                        stats["non_uk"] += 1
                        seen[item_id] = today
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

                    if cfg.CONDITION_CHECK_ENABLED and (find_red_flag(text) or find_extra_condition_flag(text, channel)):
                        stats["condition_flags"] += 1
                        seen[item_id] = today
                        continue

                    # condition filter: a KNOWN condition that is not allowed is blocked here
                    # (unknown ones are checked again after the full listing is fetched)
                    status_now = get_status(item)
                    if status_now and not condition_allowed(channel, status_now):
                        stats["bad_condition"] += 1
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
                    ex = extract_extras(item, price)

                    stats["qualified"] += 1
                    queued.add(item_id)
                    if fp:
                        queued_fps.add(fp)
                    deals.append({
                        "id": item_id, "title": title, "price": price,
                        "url": full_url(field(item, "url")), "image": get_image_url(item),
                        "photos": ex["photos"], "created_ts": ex["created_ts"],
                        "description": ex["description"] or desc.strip(),
                        "fee": ex["fee"], "fee_estimated": ex["fee_estimated"],
                        "country": ex["country"], "avatar": seller_avatar(item),
                        "rep": ex["rep"], "rep_count": ex["rep_count"],
                        "size": size_title or ex["size"],
                        "status": ex["status"],
                        "brand": brand_field or ex["brand"],
                        "resell": resell, "net_profit": net_profit, "channel": channel,
                        "tier_word": tier_word, "model": model_name, "rare_word": rare_word,
                        "misspelled": misspelled,
                        "seller_login": seller["login"], "seller_id": seller["id"],
                        "offer": offer, "profit_offer": profit_offer,
                        "era_note": era_note, "alert_under": alert_under,
                        "market_note": None, "fp": fp, "ping": ping, "hot": False,
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
                          "Vinted may be blocking GitHub's servers. I will keep trying.")
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

        # final UK + condition check, and fill in the details (fee, publish time, photos, reviews)
        verified = []
        for u in to_send:
            keep = []
            for d in u["deals"]:
                ok, reason, kind_blocked = enrich_and_verify(d)
                if ok:
                    keep.append(d)
                else:
                    if kind_blocked == "condition":
                        stats["bad_condition"] += 1
                    else:
                        stats["non_uk"] += 1
                    seen[d["id"]] = today
                    print("[BLOCKED] '" + d["title"][:50] + "': " + str(reason))
            if not keep:
                continue
            u["deals"] = keep
            if u["type"] == "bundle" and len(keep) < cfg.BUNDLE_MIN_ITEMS:
                u["type"] = "single"
            verified.append(u)

        sent = 0
        for u in verified:
            # hot streak: this seller already matched in the last 24 hours
            now_ts = time.time()
            for d in u["deals"]:
                k = seller_key(d)
                d["hot"] = bool(k and k in recent and now_ts - recent[k] < RECENT_SECONDS)

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
                    k = seller_key(d)
                    if k:
                        recent[k] = time.time()
                    if d["net_profit"] > day.get("best_profit", 0.0):
                        day["best_profit"] = d["net_profit"]
                        day["best_title"] = d["title"]
                    remember_top(day, d)
                save_state(seen, alerted, day, recent)
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
        print("Non-UK blocked:          " + str(stats["non_uk"]))
        print("Condition filter blocked: " + str(stats["bad_condition"]))
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
        save_state(seen, alerted, day, recent)


if __name__ == "__main__":
    print("Hunter sweep starting...")
    run()
    print("Sweep complete.")
