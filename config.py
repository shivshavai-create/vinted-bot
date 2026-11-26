import math
import os

# ---------------------------------------------------------------
# WEBHOOKS: one Discord channel per destination, each fed by a GitHub Secret
# (the "sniper" channel is gone: everything is sorted into these)
# ---------------------------------------------------------------
WEBHOOK_SECRETS = {
    "carhartt": "DISCORD_WEBHOOK_CARHARTT",
    "ralphlauren": "DISCORD_WEBHOOK_RALPHLAUREN",
    "footballshirts": "DISCORD_WEBHOOK_FOOTBALLSHIRTS",
    "cameras": "DISCORD_WEBHOOK_CAMERAS",
    "patagonia": "DISCORD_WEBHOOK_PATAGONIA",
    "nikeshoes": "DISCORD_WEBHOOK_NIKESHOES",
    "mertra": "DISCORD_WEBHOOK_MERTRA",
}

# Every search belongs to a CATEGORY. The category decides the rules, tag, colour,
# bot name and which destination (channel) the alert goes to.
CATEGORY_DESTINATION = {
    "carhartt": "carhartt",
    "dickies": "carhartt",
    "ralph_lauren": "ralphlauren",
    "football": "footballshirts",
    "cameras": "cameras",
    "patagonia": "patagonia",
    "shoes": "nikeshoes",
    "mertra_tnf": "mertra",
}

# (kept the old name: these are the enabled categories)
ENABLED_CHANNELS = set(CATEGORY_DESTINATION.keys())

# Destination that receives the daily summary + the "Vinted is blocking us" warning
SUMMARY_CHANNEL = "carhartt"


def destination_for(category):
    return CATEGORY_DESTINATION.get(category, SUMMARY_CHANNEL)


def get_webhook(destination):
    return os.environ.get(WEBHOOK_SECRETS.get(destination, ""))


# ---------------------------------------------------------------
# EMBED LOOK
# ---------------------------------------------------------------
CATEGORY_TAG = {
    "ralph_lauren": "[RL]",
    "football": "[FOOTBALL]",
    "cameras": "[CAM]",
    "patagonia": "[PATAGONIA]",
    "carhartt": "[CARHARTT]",
    "dickies": "[DICKIES]",
    "shoes": "[SHOES]",
    "mertra_tnf": "[MERTRA]",
}
CATEGORY_COLOUR = {
    "ralph_lauren": 0x1B2A6B,   # navy blue
    "football": 0x2ECC71,       # emerald green
    "cameras": 0x8E44AD,        # purple
    "patagonia": 0xF39C12,      # orange / amber
    "carhartt": 0xA0522D,       # brown
    "dickies": 0x7F8C8D,        # grey
    "shoes": 0xE74C3C,          # red
    "mertra_tnf": 0x1ABC9C,     # teal
}
BUNDLE_COLOUR = 0xFFD700        # gold

# Each category posts under its own bot name (shown in Discord next to the message)
CATEGORY_BOT_NAME = {
    "carhartt": "Workwear Watch \U0001F9E5",
    "dickies": "Workwear Watch \U0001F9E5",
    "ralph_lauren": "Polo Patrol \U0001F3C7",
    "football": "Kickoff Hunter \u26BD",
    "cameras": "Snap Sniper \U0001F4F7",
    "patagonia": "Fleece Finder \U0001F9F6",
    "shoes": "Sole Sniper \U0001F45F",
    "mertra_tnf": "Mertra Radar \U0001F4E1",
}
CATEGORY_ICON = {
    "carhartt": "\U0001F9E5", "dickies": "\U0001F9E5", "ralph_lauren": "\U0001F3C7",
    "football": "\u26BD", "cameras": "\U0001F4F7", "patagonia": "\U0001F9F6",
    "shoes": "\U0001F45F", "mertra_tnf": "\U0001F4E1",
}
BUNDLE_BOT_NAME = "Wardrobe Watch \U0001F4E6"
DEFAULT_BOT_NAME = "Deal Hunter"

# Optional: a picture for each bot. Paste an image link, e.g. {"cameras": "https://.../cam.png"}
CATEGORY_AVATAR = {}

# Optional: ping a Discord role for a category (turn on Developer Mode, right-click the
# role, Copy Role ID). e.g. {"cameras": "123456789012345678"}
ROLE_PING_IDS = {}

# Profit tier shown in the title: (profit at asking price, label). Highest first.
PROFIT_TIERS = [
    (40.0, "\U0001F48E JACKPOT"),
    (20.0, "\U0001F525 GREAT"),
    (8.0, "\U0001F7E2 SOLID"),
    (-9999.0, "\U0001F3AF SNIPE"),
]

# ---------------------------------------------------------------
# BUNDLES (same seller, 2+ matching items in one run = ONE gold embed)
# The bundle is posted to every channel one of its items belongs to.
# BUNDLE_ALSO_POST_TO: {"channel it contains": "extra channel to post it to"}
# ---------------------------------------------------------------
BUNDLE_MIN_ITEMS = 2
BUNDLE_MAX_ITEMS_SHOWN = 8
BUNDLE_GALLERY_IMAGES = 4       # Discord shows up to 4 photos in a grid
BUNDLE_ALSO_POST_TO = {"mertra": "carhartt"}    # set to {} to switch this off

# ---------------------------------------------------------------
# MERTRA PING
# A single Mertra windbreaker / puffer at or under the search's ping_under price
# pings @here in the mertra channel. Nothing else ever pings @here.
# ---------------------------------------------------------------
PING_TEXT = "@here \U0001F6A8 Mertra bargain!"

# ---------------------------------------------------------------
# MONEY RULES
# ---------------------------------------------------------------
MIN_BUY_PRICE = 5.0
MIN_NET_PROFIT = 6.0       # profit AFTER fees + postage
MIN_ROI = 1.0              # profit must be at least 100% of buy price
RESELL_FEE_PCT = 0.128     # set 0.0 if you resell on Vinted
POSTAGE_COST = 2.50

# Rules for one category
ROI_BY_CHANNEL = {"shoes": 0.6, "cameras": 0.6, "football": 0.8, "patagonia": 0.8}
MIN_PROFIT_BY_CHANNEL = {"shoes": 12.0, "cameras": 10.0, "football": 7.0, "patagonia": 8.0}
POSTAGE_BY_CHANNEL = {"shoes": 5.0, "cameras": 4.0, "football": 3.0, "patagonia": 3.5}

# Looser rules when a RARE keyword is found (see RARE_WORDS)
RARE_MIN_NET_PROFIT = 4.0
RARE_MIN_ROI = 0.6
RARE_MAX_BUY_MULTIPLIER = 1.3   # allowed to pay 30 percent more for rare finds

# ---------------------------------------------------------------
# ALERT LIMITS PER RUN (a bundle counts as ONE message)
# ---------------------------------------------------------------
ITEMS_PER_SEARCH = 12           # a search can override this with items=N
MAX_ALERTS_PER_RUN = 25
MAX_ALERTS_PER_CHANNEL = 3      # per category
MAX_ALERTS_BY_CHANNEL = {
    "mertra_tnf": 5, "shoes": 5, "cameras": 5, "football": 5,
    "patagonia": 4, "ralph_lauren": 4,
}

# ---------------------------------------------------------------
# STATE / REPEAT PROTECTION
# ---------------------------------------------------------------
SEEN_RETENTION_DAYS = 45
ALERTED_ID_RETENTION_DAYS = 180
ALERTED_RELIST_RETENTION_DAYS = 60
TIME_BUDGET_SECONDS = 780       # stop searching after 13 minutes and save state

# ---------------------------------------------------------------
# LIVE PRICE CHECK
# ---------------------------------------------------------------
MARKET_MIN_LISTINGS = 5
MARKET_UNDERPRICED_RATIO = 0.6

# ---------------------------------------------------------------
# OFFER SUGGESTION
# ---------------------------------------------------------------
OFFER_ENABLED = True
OFFER_PERCENT = 0.80
OFFER_MIN_PRICE = 6.0
OFFER_MESSAGE = "Hi! Would you take {offer} for this? Happy to pay today."


def max_buy_for(resell, channel, postage=None):
    """Highest buy price that still passes your profit AND ROI rules (to nearest 0.50)."""
    roi = ROI_BY_CHANNEL.get(channel, MIN_ROI)
    min_profit = MIN_PROFIT_BY_CHANNEL.get(channel, MIN_NET_PROFIT)
    if postage is None:
        postage = POSTAGE_BY_CHANNEL.get(channel, POSTAGE_COST)
    net = resell * (1 - RESELL_FEE_PCT)
    roi_bound = (net - postage) / (1 + roi)
    profit_bound = net - postage - min_profit
    return math.floor(min(roi_bound, profit_bound) * 2) / 2.0


# ---------------------------------------------------------------
# SELLER FILTERS
# ---------------------------------------------------------------
BLOCKED_SELLERS = []
MIN_SELLER_REPUTATION = 0.8
MIN_FEEDBACK_FOR_CHECK = 3

# ---------------------------------------------------------------
# BRAND CHECK: brand name must appear in title, description or brand field
# ---------------------------------------------------------------
BRAND_CHECK_ENABLED = True
BRAND_WORDS = {
    "carhartt": ["carhartt", "carhart"],
    "dickies": ["dickies", "dickie"],
    "ralph_lauren": ["ralph lauren", "ralph", "polo", "rrl", "double rl"],
    "mertra_tnf": ["mertra", "north face", "northface", "tnf"],
    "shoes": ["new balance", "newbalance", "nike", "jordan", "air max", "air force",
              "react", "huarache", "cortez", "vapormax", "vomero", "shox", "p-6000",
              "presto", "blazer"],
    "football": ["nike", "umbro", "adidas", "kappa"],
    "cameras": ["canon", "sony", "fuji", "fujifilm", "nikon", "olympus", "panasonic",
                "pentax", "ricoh", "casio", "kodak", "minolta", "konica", "yashica",
                "powershot", "ixus", "cybershot", "cyber-shot", "coolpix", "finepix",
                "lumix", "mju", "stylus", "sure shot", "sureshot"],
    "patagonia": ["patagonia"],
}

# ---------------------------------------------------------------
# CONDITION RED FLAGS ("no holes", "not worn out" are understood)
# ---------------------------------------------------------------
CONDITION_CHECK_ENABLED = True
RED_FLAG_WORDS = [
    "hole", "holes", "ripped", "rip", "rips", "torn", "tear", "tears",
    "bobbling", "pilling", "pilled", "smell", "smells", "smelly", "odour", "odor",
    "mould", "mildew", "paint", "bleach", "bleached", "missing", "broken",
    "needs repair", "needs repairing", "sold as seen", "as is", "tatty", "scruffy",
    # shoes
    "separating", "separation", "unglued", "crumbling", "crumbles", "peeling",
    "worn out", "well worn", "very worn",
    # cameras and general
    "faulty", "spares", "repairs", "for parts", "not working", "doesnt work",
    "doesn't work", "wont turn on", "won't turn on", "cracked",
    "dead pixel", "dead pixels",
]

# ---------------------------------------------------------------
# VINTAGE vs MODERN (Carhartt + Dickies only)
# ---------------------------------------------------------------
WORKWEAR_VINTAGE_WORDS = [
    "vintage", "70s", "80s", "90s", "1970s", "1980s", "1990s",
    "y2k", "retro", "old school", "made in usa", "usa made",
]
MODERN_RESELL_FACTOR = {"carhartt": 0.5, "dickies": 0.5}

# ---------------------------------------------------------------
# FOOTBALL SHIRTS: must look 90s/00s (a vintage word, a year 1990-2009,
# a season like 98/99, or a classic sponsor). Modern seasons (2010+) are skipped.
# ---------------------------------------------------------------
FOOTBALL_VINTAGE_WORDS = [
    "vintage", "retro", "90s", "00s", "1990s", "2000s", "y2k", "classic", "throwback",
]
FOOTBALL_SPONSORS = [
    "pirelli", "opel", "sharp", "carlsberg", "carling", "o2", "vodafone", "jvc", "mci",
    "nec", "samsung", "brother", "ericsson", "dreamcast", "sega", "emirates",
    "aon", "sanderson", "fiat", "parmalat", "autoglass", "thomas cook", "mobil",
    "bwin", "hitachi", "commodore", "amstrad", "crown paints", "newcastle brown",
]
# A football listing must mention one of these (so random "shirt" listings are skipped)
FOOTBALL_WORDS = [
    "football", "soccer", "home", "away", "third", "jersey", "kit", "fc", "utd", "united",
    "city", "arsenal", "chelsea", "liverpool", "tottenham", "spurs", "everton", "celtic",
    "rangers", "england", "scotland", "wales", "ireland", "brazil", "germany", "holland",
    "netherlands", "italy", "spain", "france", "argentina", "portugal", "juventus", "milan",
    "inter", "barcelona", "real madrid", "ajax", "psv", "newcastle", "leeds", "villa",
    "west ham", "sunderland", "bayern", "roma", "lazio", "napoli", "leicester", "forest",
]

# ---------------------------------------------------------------
# CAMERAS: untested ones are allowed but priced lower
# ---------------------------------------------------------------
UNTESTED_WORDS = ["untested", "not tested", "unable to test", "cant test", "can't test"]
UNTESTED_RESELL_FACTOR = {"cameras": 0.7}

# ---------------------------------------------------------------
# SIZES
# ---------------------------------------------------------------
TOPS = {"m", "medium", "l", "large", "xl"}
FOOTBALL_SIZES = {"s", "small", "m", "medium", "l", "large", "xl"}
BOTTOM_RANGE = (28, 38)
SHOE_RANGE = (8, 11)            # UK sizes (EU sizes are converted automatically)

# ---------------------------------------------------------------
# JUNK / KIDS FILTERS
# ---------------------------------------------------------------
BANNED_WORDS = [
    "realtree", "style", "styled", "inspired", "type",
    "rep", "reps", "replica", "fake", "unbranded", "pandabuy", "taobao", "dhgate",
    "shorts", "satisfactory", "damaged", "flawed", "stained",
    "rework", "reworked", "re-work", "re-worked", "reworks",
]
BANNED_PHRASES = [
    "camo tree", "fair condition", "heavy wear", "spare or repair",
    "not authentic", "not genuine", "not a genuine", "isn't authentic", "isnt authentic",
    "unauthentic", "inauthentic",
]

# Words from BANNED_WORDS that do NOT apply to one category
# (camera listings often say "battery type", "SD card type" etc.)
BANNED_EXEMPT_BY_CHANNEL = {
    "cameras": ["type", "style", "styled"],
}

# Extra banned words for ONE category (checked in title + description)
EXTRA_BANNED_BY_CHANNEL = {
    "ralph_lauren": [
        "faded",
        "chaps", "lauren ralph lauren", "lauren by ralph lauren",
    ],
    "shoes": [
        "box only", "empty box", "empty shoebox", "one shoe", "single shoe",
        "left shoe", "right shoe", "odd shoe", "whatsapp", "bank transfer", "paypal friends",
    ],
    "cameras": [
        "box only", "empty box", "dummy", "fake camera", "disposable", "cctv", "webcam",
        "action cam", "gopro", "whatsapp", "bank transfer", "paypal friends",
    ],
    "football": [
        "custom", "customised", "personalised", "personalized", "bootleg", "unofficial",
        "fan made", "fan-made", "retro style", "retro-style",
    ],
    "patagonia": [
        "vest", "gilet", "beanie", "hat", "gloves", "t-shirt", "tee", "shorts",
    ],
}

# Banned words checked in the TITLE only (a basic polo or tee = no thanks)
TITLE_EXCLUDE_BY_CHANNEL = {
    "ralph_lauren": [
        "polo shirt", "polo shirts", "t-shirt", "tshirt", "t shirt", "tee", "tees",
        "short sleeve", "short sleeved", "short-sleeve", "short sleeves", "s/s",
        "vest", "tank", "swim",
    ],
    "football": [
        "poster", "scarf", "hat", "keyring", "mug", "programme", "program", "socks",
        "boots", "book", "magazine",
    ],
}

KIDS_WORDS = [
    "kids", "kid", "boy", "boys", "girl", "girls", "child", "children", "childrens",
    "youth", "junior", "juniors", "toddler", "baby", "infant",
    "gs", "ps", "td", "grade school", "preschool", "pre-school",
]

# ---------------------------------------------------------------
# ACCESSORY FILTER: blocks these when listed ON THEIR OWN (title only).
# A camera sold WITH one ("with charger", "+ case") is fine. "case FOR Canon" is blocked.
# ---------------------------------------------------------------
ACCESSORY_WORDS_BY_CHANNEL = {
    "shoes": [
        "laces", "shoe laces", "insoles", "insole", "shoe box", "shoebox", "shoe tree",
        "shoe trees", "cleaner", "cleaning kit", "protector", "dust bag", "shoe bag",
        "keyring", "keychain", "sticker", "stickers", "poster",
    ],
    "cameras": [
        "case", "pouch", "bag", "strap", "lens", "lenses", "battery", "batteries",
        "charger", "cable", "lead", "sd card", "memory card", "cap", "hood", "tripod",
        "manual", "cover", "filter", "adapter", "screen protector", "usb",
    ],
}

CHECKLISTS = {
    "carhartt": "Check back patch and pocket tag, zip brand (YKK/Ideal), wash tag and stitching",
    "dickies": "Check logo quality, wash tag, stitching, hardware and zip",
    "ralph_lauren": "Check pony stitching and tag, RN number / care tag, vintage label era",
    "mertra_tnf": "Fakes exist for both brands: check logo stitching, YKK zips, labels and RN/fill tags, ask for tag photos",
    "shoes": "Ask for sole and inside-tag photos. Check sole wear and separation, smell, and match the style code on the tongue tag",
    "football": "Reps are everywhere: check the tag, stitched badge and sponsor font, era-correct kit details, ask for tag photos",
    "cameras": "Ask for a photo switched on. Check lens, screen, battery door and charger. Test before you list it",
    "patagonia": "Check the tag and STY code, zips and snaps, pilling under the arms, ask for tag photos",
}

# ---------------------------------------------------------------
# MODEL TIERS: a model word in the title can RAISE the resell price
# (never lowers it). The most SPECIFIC matching word wins.
# Prices are BRUTAL on purpose (well under real sold prices).
# ---------------------------------------------------------------
MODEL_TIERS = {
    "carhartt": [
        {"words": ["detroit"], "resell": 34},
        {"words": ["arctic"], "resell": 40},
        {"words": ["chore coat", "michigan"], "resell": 34},
        {"words": ["santa fe"], "resell": 32},
        {"words": ["double knee"], "resell": 24},
    ],
    "dickies": [],
    "ralph_lauren": [
        {"words": ["rugby"], "resell": 30},
        {"words": ["harrington"], "resell": 40},
        {"words": ["bear"], "resell": 30},
        {"words": ["stadium", "snow beach"], "resell": 55},
        {"words": ["purple label", "double rl", "rrl"], "resell": 70},
    ],
    "mertra_tnf": [
        {"words": ["heat reactive", "heat-reactive"], "resell": 75},
    ],
    "shoes": [
        # --- New Balance ---
        {"words": ["9060"], "resell": 55},
        {"words": ["2002r"], "resell": 55},
        {"words": ["1906r"], "resell": 55},
        {"words": ["550"], "resell": 42},
        {"words": ["327"], "resell": 32},
        {"words": ["530"], "resell": 30},
        {"words": ["996"], "resell": 32},
        {"words": ["998"], "resell": 60},
        {"words": ["576"], "resell": 55},
        {"words": ["990v3", "990 v3"], "resell": 85},
        {"words": ["990v4", "990 v4"], "resell": 75},
        {"words": ["991"], "resell": 65},
        # --- Nike ---
        {"words": ["air force 1", "air force one", "af1"], "resell": 30},
        {"words": ["air max 90"], "resell": 38},
        {"words": ["air max 95"], "resell": 42},
        {"words": ["air max 97"], "resell": 42},
        {"words": ["air max 98"], "resell": 40},
        {"words": ["air max plus"], "resell": 42},
        {"words": ["air max 1"], "resell": 40},
        {"words": ["air max 270"], "resell": 35},
        {"words": ["dunk low"], "resell": 38},
        {"words": ["jordan 1"], "resell": 38},
        {"words": ["react vision"], "resell": 35},
        {"words": ["react element"], "resell": 40},
        {"words": ["infinity run"], "resell": 35},
        {"words": ["vapormax"], "resell": 42},
        {"words": ["huarache"], "resell": 30},
        {"words": ["cortez"], "resell": 28},
        {"words": ["vomero 5"], "resell": 50},
        {"words": ["shox"], "resell": 50},
        {"words": ["p-6000"], "resell": 38},
        {"words": ["blazer"], "resell": 28},
        {"words": ["presto"], "resell": 30},
    ],
    # Cameras: BRUTAL. Family searches only alert when one of these models shows up.
    "cameras": [
        {"words": ["ixus 70", "ixus70", "ixus 80", "ixus80"], "resell": 35},
        {"words": ["ixus 75", "ixus 85", "ixus 90", "ixus 95"], "resell": 30},
        {"words": ["ixus 100"], "resell": 30},
        {"words": ["ixus 860"], "resell": 28},
        {"words": ["ixus 870"], "resell": 30},
        {"words": ["ixus 960"], "resell": 32},
        {"words": ["ixus 115", "ixus 120", "ixus 125", "ixus 130"], "resell": 25},
        {"words": ["powershot g10"], "resell": 45},
        {"words": ["powershot g11", "powershot g12", "powershot g9"], "resell": 50},
        {"words": ["powershot s90"], "resell": 38},
        {"words": ["powershot s95"], "resell": 45},
        {"words": ["rx100"], "resell": 90},
        {"words": ["dsc-w"], "resell": 25},
        {"words": ["dsc-t"], "resell": 28},
        {"words": ["f31fd", "finepix f30"], "resell": 40},
        {"words": ["f200exr", "f300exr", "f550exr"], "resell": 35},
        {"words": ["mju ii", "mju 2", "mju-ii", "mju iii", "stylus epic"], "resell": 65},
        {"words": ["mju", "stylus"], "resell": 35},
        {"words": ["lx3", "lx5"], "resell": 55},
        {"words": ["lx7"], "resell": 80},
        {"words": ["dmc-tz", "dmc-fz"], "resell": 30},
        {"words": ["sure shot", "sureshot"], "resell": 22},
        {"words": ["espio"], "resell": 22},
        {"words": ["trip 35"], "resell": 55},
    ],
    "football": [
        {"words": ["sharp"], "resell": 40},
        {"words": ["pirelli"], "resell": 35},
        {"words": ["carlsberg"], "resell": 32},
        {"words": ["opel"], "resell": 32},
    ],
    "patagonia": [
        {"words": ["retro-x", "retro x", "retrox"], "resell": 50},
        {"words": ["retro pile"], "resell": 45},
        {"words": ["snap-t", "snap t", "snapt"], "resell": 40},
        {"words": ["synchilla"], "resell": 36},
        {"words": ["better sweater"], "resell": 36},
    ],
}

# ---------------------------------------------------------------
# RARE KEYWORDS (loosen the profit rules when found).
# Searches with alert_under ignore this.
# ---------------------------------------------------------------
RARE_WORDS = {
    "carhartt": ["made in usa", "usa made", "j97", "j01", "michigan", "arctic",
                 "blanket lined", "chore coat"],
    "dickies": ["made in usa", "usa made", "ike jacket"],
    "ralph_lauren": ["made in usa", "usa made", "stadium", "snow beach", "p-wing",
                     "polo bear", "hi tech", "rrl", "double rl", "purple label",
                     "polo sport", "polo country"],
    "mertra_tnf": ["heat reactive", "heat-reactive", "colour change", "color change"],
    "shoes": ["made in usa", "made in england", "made in uk", "miusa", "miuk"],
    "cameras": ["leica", "contax", "yashica", "mju ii", "stylus epic", "rollei", "minox"],
    "football": ["player issue", "match worn", "match issue", "matchworn"],
    "patagonia": ["made in usa", "usa made", "deep pile", "retro pile"],
}


# ---------------------------------------------------------------
# SEARCHES
# _t(query, resell, category, size_kind) works out max_buy for you.
# Extra options:
#   max_buy=N        force a buy limit
#   min_buy=N        lowest price to alert on (fake guard)
#   alert_under=N    alert for ANY listing at N pounds or less, profit rules skipped
#   ping_under=N     (mertra only) ping @here when the price is N or less
#   no_modern=True   send nothing for modern (non-vintage) items
#   require_any=[..] listing must contain one of these words
#   items=N          how many newest listings to check for this search
#   postage=N        your postage cost for this item
# size_kind: tops, bottoms, shoes, football, or None (no size filter, kids still blocked)
# ---------------------------------------------------------------
def _t(query, resell, channel, kind, max_buy=None, **extra):
    if max_buy is None:
        max_buy = extra.get("alert_under") or max_buy_for(resell, channel, extra.get("postage"))
    d = {"query": query, "resell": resell, "max_buy": max_buy, "channel": channel, "kind": kind}
    d.update(extra)
    return d


def _shoe(query, resell, **extra):
    """A shoe search: UK sizes 8 to 11, minimum buy 8 pounds."""
    extra.setdefault("min_buy", 8)
    extra.setdefault("items", 20)
    return _t(query, resell, "shoes", "shoes", **extra)


# --- word lists used by searches ---
NF_PUFFER_WORDS = ["puffer", "puffa", "puffy", "nuptse", "down", "padded", "quilted"]
MERTRA_HOODIE_WORDS = ["hoodie", "hoody", "hooded"]
MERTRA_WINDBREAKER_WORDS = ["windbreaker", "wind breaker", "wind jacket", "shell"]
MERTRA_PUFFER_WORDS = ["puffer", "puffa", "puffy", "padded", "quilted"]

# Ralph Lauren: only knits, quarter zips, rugby shirts and jackets (no basic polos / tees)
RL_TYPE_WORDS = [
    "knit", "knitted", "cable", "jumper", "sweater", "pullover", "cardigan",
    "quarter zip", "quarter-zip", "1/4 zip", "half zip", "half-zip", "zip neck",
    "rugby", "jacket", "harrington", "coat", "bomber",
]

CAMERA_WORDS = [
    "powershot", "ixus", "cyber-shot", "cybershot", "coolpix", "finepix", "mju",
    "stylus", "lumix", "digicam", "35mm", "camera", "sure shot", "sureshot", "dsc",
    "digital camera", "point and shoot",
]

PATAGONIA_WORDS = [
    "fleece", "synchilla", "snap-t", "snap t", "better sweater", "retro-x", "retro x", "retro pile",
]


def _rl(query, resell, **extra):
    extra.setdefault("require_any", RL_TYPE_WORDS)
    return _t(query, resell, "ralph_lauren", "tops", **extra)


def _cam(query, resell, **extra):
    """A camera search: no size filter, minimum buy 8 pounds (junk guard)."""
    extra.setdefault("min_buy", 8)
    extra.setdefault("items", 20)
    extra.setdefault("require_any", CAMERA_WORDS)
    return _t(query, resell, "cameras", None, **extra)


def _foot(query, resell, **extra):
    """A football shirt search: sizes S M L XL, minimum buy 6 pounds."""
    extra.setdefault("min_buy", 6)
    extra.setdefault("items", 25)
    extra.setdefault("require_any", FOOTBALL_WORDS)
    return _t(query, resell, "football", "football", **extra)


def _pat(query, resell, **extra):
    extra.setdefault("min_buy", 8)
    extra.setdefault("items", 20)
    extra.setdefault("require_any", PATAGONIA_WORDS)
    return _t(query, resell, "patagonia", "tops", **extra)


TARGETS = [
    # ----- CARHARTT (resell = vintage price; modern is cut by MODERN_RESELL_FACTOR) -----
    _t("carhartt jacket", 30, "carhartt", "tops"),
    _t("carhartt detroit jacket", 30, "carhartt", "tops"),
    _t("carhartt santa fe jacket", 30, "carhartt", "tops"),
    _t("carhartt active jacket", 30, "carhartt", "tops"),
    _t("carhartt chore coat", 30, "carhartt", "tops"),
    _t("carhartt arctic jacket", 30, "carhartt", "tops"),
    _t("carhartt michigan coat", 30, "carhartt", "tops"),
    _t("carhartt blanket lined jacket", 30, "carhartt", "tops"),
    _t("carhartt vintage jacket", 30, "carhartt", "tops"),
    _t("carhartt vintage coat", 20, "carhartt", "tops"),
    _t("carhartt hoodie", 20, "carhartt", "tops"),
    _t("carhartt tee", 12, "carhartt", "tops"),
    _t("carhartt jeans", 15, "carhartt", "bottoms", alert_under=8, no_modern=True),
    _t("carhartt carpenter jeans", 15, "carhartt", "bottoms", alert_under=8, no_modern=True),
    _t("carhartt double knee pants", 22, "carhartt", "bottoms"),
    _t("carhartt single knee pants", 17, "carhartt", "bottoms"),

    # ----- DICKIES -----
    _t("dickies eisenhower jacket", 27, "dickies", "tops"),
    _t("dickies duck jacket", 27, "dickies", "tops"),
    _t("dickies work jacket", 27, "dickies", "tops"),
    _t("dickies jeans", 14, "dickies", "bottoms", alert_under=7, no_modern=True),
    _t("dickies carpenter jeans", 14, "dickies", "bottoms", alert_under=7, no_modern=True),

    # ----- [RL] RALPH LAUREN: knits, quarter zips, rugby, jackets, rare tags -----
    _rl("ralph lauren knit", 18),
    _rl("ralph lauren cable knit jumper", 18),
    _rl("ralph lauren fair isle jumper", 28),
    _rl("ralph lauren aran jumper", 25),
    _rl("ralph lauren bear jumper", 30),
    _rl("ralph lauren cardigan", 20),
    _rl("ralph lauren quarter zip", 20),
    _rl("ralph lauren half zip jumper", 20),
    _rl("ralph lauren rugby shirt", 26),
    _rl("ralph lauren harrington jacket", 36, max_buy=18),
    _rl("ralph lauren jacket", 28),
    _rl("ralph lauren varsity jacket", 30),
    _rl("ralph lauren stadium jacket", 55),
    _rl("ralph lauren snow beach", 55),
    _rl("polo sport jacket", 30),
    _rl("polo sport knit", 24),
    _rl("polo country", 28),
    _rl("ralph lauren rrl", 65),
    _rl("ralph lauren double rl", 65),
    _rl("ralph lauren purple label", 70),

    # ----- THE NORTH FACE: PUFFERS ONLY (goes to the mertra channel) -----
    _t("north face puffer jacket", 32, "mertra_tnf", "tops", alert_under=16, require_any=NF_PUFFER_WORDS),
    _t("north face nuptse", 32, "mertra_tnf", "tops", alert_under=16, require_any=NF_PUFFER_WORDS),
    _t("north face down jacket", 32, "mertra_tnf", "tops", alert_under=16, require_any=NF_PUFFER_WORDS),

    # ----- MERTRA: hoodies, windbreakers, puffers (all sizes, kids blocked) -----
    # ping_under = a single bargain at or under this price pings @here
    _t("mertra hoodie", 25, "mertra_tnf", None, alert_under=15, items=30, require_any=MERTRA_HOODIE_WORDS),
    _t("mertra windbreaker", 40, "mertra_tnf", None, alert_under=28, ping_under=25, items=30,
       require_any=MERTRA_WINDBREAKER_WORDS),
    _t("mertra shell jacket", 40, "mertra_tnf", None, alert_under=28, ping_under=25, items=30,
       require_any=MERTRA_WINDBREAKER_WORDS),
    _t("mertra puffer", 60, "mertra_tnf", None, alert_under=42, ping_under=38, items=30,
       require_any=MERTRA_PUFFER_WORDS),
    _t("mertra heat reactive puffer", 75, "mertra_tnf", None, alert_under=50, ping_under=45, items=30,
       require_any=MERTRA_PUFFER_WORDS),

    # ----- [FOOTBALL] vintage shirts, S M L XL, 90s/00s Nike Umbro Adidas Kappa -----
    _foot("vintage football shirt", 28),
    _foot("90s football shirt", 28),
    _foot("00s football shirt", 28),
    _foot("retro football shirt", 26),
    _foot("umbro football shirt", 28),
    _foot("umbro 90s shirt", 28),
    _foot("kappa football shirt", 30),
    _foot("adidas football shirt 90s", 28),
    _foot("adidas football shirt 00s", 28),
    _foot("nike football shirt 90s", 28),
    _foot("nike football shirt 00s", 28),
    _foot("pirelli football shirt", 35),
    _foot("opel football shirt", 32),
    _foot("sharp football shirt", 38),
    _foot("carlsberg football shirt", 32),
    _foot("o2 football shirt", 28),
    _foot("vodafone football shirt", 28),
    _foot("jvc football shirt", 30),
    _foot("samsung football shirt", 28),
    _foot("manchester united football shirt 90s", 32),
    _foot("arsenal football shirt 90s", 30),
    _foot("liverpool football shirt 90s", 30),
    _foot("chelsea football shirt 90s", 30),
    _foot("tottenham football shirt 90s", 28),
    _foot("newcastle football shirt 90s", 28),
    _foot("everton football shirt 90s", 28),
    _foot("leeds football shirt 90s", 28),
    _foot("england football shirt 90s", 30),
    _foot("celtic football shirt vintage", 28),
    _foot("rangers football shirt vintage", 28),
    _foot("italy football shirt 90s", 28),
    _foot("brazil football shirt 90s", 30),

    # ----- [CAM] cameras only (accessories blocked, untested = resell x0.7) -----
    _cam("canon ixus 70", 35),
    _cam("canon ixus 80", 35),
    _cam("canon ixus 75", 30),
    _cam("canon ixus 85", 30),
    _cam("canon ixus 100", 30),
    _cam("canon ixus 860", 28),
    _cam("canon ixus 870", 30),
    _cam("canon ixus 960", 32),
    _cam("canon powershot g10", 45),
    _cam("canon powershot g11", 50),
    _cam("canon powershot s95", 45),
    _cam("canon powershot s90", 38),
    _cam("canon ixus", 25, items=30),
    _cam("canon powershot", 25, items=30),
    _cam("sony cybershot dsc-w", 25, items=30),
    _cam("sony cybershot dsc-t", 28),
    _cam("sony cyber-shot", 25, items=30),
    _cam("sony rx100", 90),
    _cam("fujifilm finepix f31fd", 40),
    _cam("fujifilm finepix f200exr", 35),
    _cam("fujifilm finepix", 25, items=30),
    _cam("nikon coolpix", 25, items=30),
    _cam("olympus mju ii", 65),
    _cam("olympus mju", 35),
    _cam("olympus stylus", 35),
    _cam("olympus trip 35", 55),
    _cam("panasonic lumix lx3", 55),
    _cam("panasonic lumix lx5", 55),
    _cam("panasonic lumix", 25, items=30),
    _cam("canon sure shot 35mm", 22),
    _cam("pentax espio", 22),
    _cam("35mm compact camera", 25, items=30),
    _cam("digicam", 25, items=30),

    # ----- [PATAGONIA] fleeces: Synchilla, Snap-T, Better Sweater, Retro-X -----
    _pat("patagonia synchilla", 36),
    _pat("patagonia lightweight synchilla", 32),
    _pat("patagonia snap t", 40),
    _pat("patagonia better sweater", 36),
    _pat("patagonia retro x", 50),
    _pat("patagonia retro pile", 45),
    _pat("patagonia fleece jacket", 32, items=30),
    _pat("patagonia pullover fleece", 30, items=30),
    _pat("patagonia vintage fleece", 36),
    _pat("patagonia fleece", 30, items=30),

    # ===============================================================
    # SHOES: New Balance and Nike, well-known pairs. UK sizes 8 to 11.
    # The model is recognised in the title by MODEL_TIERS and can raise the
    # search's starting resell price.
    # ===============================================================

    # --- New Balance ---
    _shoe("new balance 9060", 55),
    _shoe("new balance 2002r", 55),
    _shoe("new balance 1906r", 55),
    _shoe("new balance 550", 42),
    _shoe("new balance 327", 32),
    _shoe("new balance 530", 30),
    _shoe("new balance 996", 32),
    _shoe("new balance 998", 60),
    _shoe("new balance 576", 55),
    _shoe("new balance 990v3", 85),
    _shoe("new balance 990v4", 75),
    _shoe("new balance 991", 65),
    _shoe("new balance made in usa", 28, items=30),
    _shoe("new balance made in england", 28, items=30),
    _shoe("new balance trainers", 28, items=30),

    # --- Nike ---
    _shoe("nike air force 1", 30),
    _shoe("nike air max 90", 38),
    _shoe("nike air max 95", 42),
    _shoe("nike air max 97", 42),
    _shoe("nike air max 98", 40),
    _shoe("nike air max plus", 42),
    _shoe("nike air max 1", 40),
    _shoe("nike air max 270", 35),
    _shoe("nike dunk low", 38),
    _shoe("air jordan 1 mid", 38),
    _shoe("nike react vision", 35),
    _shoe("nike react element 55", 40),
    _shoe("nike react infinity run", 35),
    _shoe("nike vapormax", 42),
    _shoe("nike huarache", 30),
    _shoe("nike cortez", 28),
    _shoe("nike vomero 5", 50),
    _shoe("nike shox", 50),
    _shoe("nike p-6000", 38),
    _shoe("nike blazer", 28),
    _shoe("nike air presto", 30),
    _shoe("nike react", 28, items=30),
    _shoe("nike air max", 28, items=30),
]

# ---------------------------------------------------------------
# MISSPELLING HUNTER
# (category, misspellings, [(product word, size kind, resell, optional extras)])
# The listing TITLE must contain the misspelling to count.
# ---------------------------------------------------------------
MISSPELL_PLAN = [
    ("carhartt", ["carhart", "carharrt", "carhatt"],
     [("jacket", "tops", 30),
      ("jeans", "bottoms", 15, {"alert_under": 8, "no_modern": True})]),
    ("dickies", ["dickie", "dickeys"],
     [("jacket", "tops", 27)]),
    ("ralph_lauren", ["ralf lauren", "ralph laren", "ralph lauran"],
     [("jumper", "tops", 18, {"require_any": RL_TYPE_WORDS})]),
    ("patagonia", ["patagonai", "patagona", "patogonia"],
     [("fleece", "tops", 36, {"min_buy": 8, "require_any": PATAGONIA_WORDS})]),
    ("cameras", ["cannon"],
     [("ixus", None, 25, {"min_buy": 8, "require_any": CAMERA_WORDS}),
      ("powershot", None, 25, {"min_buy": 8, "require_any": CAMERA_WORDS})]),
    ("mertra_tnf", ["northface", "tnf"],
     [("puffer", "tops", 32, {"alert_under": 16, "require_any": NF_PUFFER_WORDS})]),
    ("mertra_tnf", ["mertrra", "meertra"],
     [("puffer", None, 60, {"alert_under": 42, "ping_under": 38, "items": 30,
                            "require_any": MERTRA_PUFFER_WORDS})]),
]


def _misspelled_targets():
    out = []
    for channel, spellings, products in MISSPELL_PLAN:
        for sp in spellings:
            for prod in products:
                word, kind, resell = prod[0], prod[1], prod[2]
                extras = dict(prod[3]) if len(prod) > 3 else {}
                out.append(_t(sp + " " + word, resell, channel, kind,
                              must_match=[sp], misspelled=True, **extras))
    return out


TARGETS = TARGETS + _misspelled_targets()
