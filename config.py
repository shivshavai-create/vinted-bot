import math
import os

# ---------------------------------------------------------------
# WEBHOOKS: which GitHub Secret feeds which Discord channel
# ---------------------------------------------------------------
WEBHOOK_SECRETS = {
    "carhartt": "DISCORD_WEBHOOK_CARHARTT",
    "dickies": "DISCORD_WEBHOOK_CARHARTT",
    "ralph_lauren": "DISCORD_WEBHOOK_RALPHLAUREN",
    "mertra_tnf": "DISCORD_WEBHOOK_MERTRA",
    "patagonia_arcteryx": "DISCORD_WEBHOOK_PATAGONIA",
}


def get_webhook(channel):
    return os.environ.get(WEBHOOK_SECRETS.get(channel, ""))


ENABLED_CHANNELS = {"carhartt", "dickies", "ralph_lauren", "mertra_tnf", "patagonia_arcteryx"}

# Which channel receives the once-a-day summary message
SUMMARY_CHANNEL = "carhartt"

# ---------------------------------------------------------------
# MONEY RULES
# ---------------------------------------------------------------
MIN_BUY_PRICE = 5.0
MIN_NET_PROFIT = 6.0       # profit AFTER fees + postage
MIN_ROI = 1.0              # profit must be at least 100% of buy price
RESELL_FEE_PCT = 0.128     # set 0.0 if you resell on Vinted
POSTAGE_COST = 2.50

# Optional stricter rules for one channel, e.g. {"patagonia_arcteryx": 1.5}
ROI_BY_CHANNEL = {}
MIN_PROFIT_BY_CHANNEL = {}

# Looser rules when a RARE / good-type keyword is found (see RARE_WORDS)
RARE_MIN_NET_PROFIT = 4.0
RARE_MIN_ROI = 0.6
RARE_MAX_BUY_MULTIPLIER = 1.3   # allowed to pay 30 percent more for rare finds

# ---------------------------------------------------------------
# ALERT LIMITS PER RUN
# Each channel gets its own cap so one channel can never push the others out.
# ---------------------------------------------------------------
ITEMS_PER_SEARCH = 10           # a search can override this with items=N
MAX_ALERTS_PER_RUN = 12
MAX_ALERTS_PER_CHANNEL = 3
MAX_ALERTS_BY_CHANNEL = {"mertra_tnf": 5}

# ---------------------------------------------------------------
# AUTHENTIC / REAL CLAIMS (Patagonia + Arc'teryx)
# A seller saying "authentic" or "real" is a good sign (not proof!):
# the alert says so, ranks higher, and allows a slightly higher buy limit.
# "not authentic" / "no real" are understood and ignored.
# ---------------------------------------------------------------
AUTHENTIC_BONUS_CHANNELS = {"patagonia_arcteryx"}
AUTHENTIC_WORDS = [
    "100% authentic", "100% real", "guaranteed authentic", "guaranteed real",
    "authenticated", "authentic", "genuine", "legit", "real",
]
AUTHENTIC_MAX_BUY_MULTIPLIER = 1.15
AUTHENTIC_RANK_BONUS = 10.0     # added to the profit when ranking alerts

# ---------------------------------------------------------------
# OFFER SUGGESTION
# Alerts show an offer price and the profit with AND without it.
# ---------------------------------------------------------------
OFFER_ENABLED = True
OFFER_PERCENT = 0.80            # offer 80 percent of the asking price
OFFER_MIN_PRICE = 6.0           # no offer suggested on very cheap items
OFFER_MESSAGE = "Hi! Would you take {offer} for this? Happy to pay today."


def max_buy_for(resell, channel):
    """Highest buy price that still passes your profit AND ROI rules (to nearest 0.50)."""
    roi = ROI_BY_CHANNEL.get(channel, MIN_ROI)
    min_profit = MIN_PROFIT_BY_CHANNEL.get(channel, MIN_NET_PROFIT)
    net = resell * (1 - RESELL_FEE_PCT)
    roi_bound = (net - POSTAGE_COST) / (1 + roi)
    profit_bound = net - POSTAGE_COST - min_profit
    return math.floor(min(roi_bound, profit_bound) * 2) / 2.0


# ---------------------------------------------------------------
# SELLER FILTERS
# ---------------------------------------------------------------
BLOCKED_SELLERS = []            # usernames to always ignore, e.g. ["someuser"]
MIN_SELLER_REPUTATION = 0.8     # 0 to 1 (0.8 = 80 percent positive)
MIN_FEEDBACK_FOR_CHECK = 3      # ignore rating if seller has fewer reviews

# ---------------------------------------------------------------
# BRAND CHECK: brand name must appear in title, description or brand field
# ---------------------------------------------------------------
BRAND_CHECK_ENABLED = True
BRAND_WORDS = {
    "carhartt": ["carhartt", "carhart"],
    "dickies": ["dickies", "dickie"],
    "ralph_lauren": ["ralph lauren", "ralph", "polo"],
    "mertra_tnf": ["mertra", "north face", "northface", "tnf"],
    "patagonia_arcteryx": ["patagonia", "arcteryx", "arc'teryx", "arc\u2019teryx",
                           "arc teryx", "arc-teryx"],
}

# ---------------------------------------------------------------
# CONDITION RED FLAGS ("no holes", "without stains" are understood)
# ---------------------------------------------------------------
CONDITION_CHECK_ENABLED = True
RED_FLAG_WORDS = [
    "hole", "holes", "ripped", "rip", "rips", "torn", "tear", "tears",
    "bobbling", "pilling", "pilled", "smell", "smells", "smelly", "odour", "odor",
    "mould", "mildew", "paint", "bleach", "bleached", "missing", "broken",
    "needs repair", "needs repairing", "sold as seen", "as is", "tatty", "scruffy",
]

# ---------------------------------------------------------------
# VINTAGE vs MODERN (Carhartt + Dickies only)
# Any of these words in the title or description = vintage, and the
# resell price you set in TARGETS is used as it is.
# Anything else = modern: the resell price is multiplied by the factor
# below (0.5 = half) and max buy is recalculated.
# A search marked no_modern=True sends NOTHING for modern items.
# ---------------------------------------------------------------
WORKWEAR_VINTAGE_WORDS = [
    "vintage", "70s", "80s", "90s", "1970s", "1980s", "1990s",
    "y2k", "retro", "old school", "made in usa", "usa made",
]
VINTAGE_RESELL_FACTOR = {}      # empty = vintage uses the TARGETS prices exactly
MODERN_RESELL_FACTOR = {"carhartt": 0.5, "dickies": 0.5}

# ---------------------------------------------------------------
# SIZES
# ---------------------------------------------------------------
TOPS = {"m", "medium", "l", "large", "xl"}
BOTTOM_RANGE = (28, 38)
SHOE_RANGE = (7, 11)

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

# Extra banned words for ONE channel only
EXTRA_BANNED_BY_CHANNEL = {
    "ralph_lauren": [
        "faded",
        "polo sport", "polo sports", "polosport", "polo-sport",
        "chaps", "lauren ralph lauren", "lauren by ralph lauren",
    ],
}

KIDS_WORDS = [
    "kids", "kid", "boy", "boys", "girl", "girls", "child", "children", "childrens",
    "youth", "junior", "juniors", "toddler", "baby", "infant",
]

CHECKLISTS = {
    "carhartt": "Check back patch and pocket tag, zip brand (YKK/Ideal), wash tag and stitching",
    "dickies": "Check logo quality, wash tag, stitching, hardware and zip",
    "ralph_lauren": "Check pony stitching and tag, RN number / care tag, vintage label era",
    "mertra_tnf": "Fakes exist for both brands: check logo stitching, YKK zips, labels and RN/fill tags, ask for tag photos",
    "patagonia_arcteryx": "Patagonia: check STY style code tag, zips and logo stitching. Arc'teryx: check made-in label, ID/serial tag, laminated zips. Ask for tag photos",
}

# ---------------------------------------------------------------
# MODEL TIERS: a model word in the title can RAISE the resell price
# (never lowers it). max_buy is worked out automatically.
# These are the "good types" being promoted.
# ---------------------------------------------------------------
MODEL_TIERS = {
    "carhartt": [
        {"words": ["detroit"], "resell": 42},
        {"words": ["arctic"], "resell": 48},
        {"words": ["chore coat", "michigan"], "resell": 42},
        {"words": ["santa fe"], "resell": 40},
        {"words": ["double knee"], "resell": 30},
    ],
    "dickies": [],
    "ralph_lauren": [
        {"words": ["rugby"], "resell": 38},
        {"words": ["harrington"], "resell": 48},
        {"words": ["bear"], "resell": 35},
        {"words": ["purple label", "double rl", "rrl"], "resell": 80},
    ],
    "mertra_tnf": [
        {"words": ["heat reactive", "heat-reactive"], "resell": 85},
    ],
    "patagonia_arcteryx": [
        {"words": ["retro-x", "retro x"], "resell": 60},
        {"words": ["synchilla", "snap-t", "snap t"], "resell": 50},
        {"words": ["nano puff"], "resell": 60},
        {"words": ["down sweater"], "resell": 70},
        {"words": ["torrentshell"], "resell": 40},
        {"words": ["atom"], "resell": 90},
        {"words": ["proton", "gamma"], "resell": 90},
        {"words": ["beta"], "resell": 110},
        {"words": ["zeta"], "resell": 110},
        {"words": ["alpha"], "resell": 130},
    ],
}

# ---------------------------------------------------------------
# RARE / GOOD-TYPE KEYWORDS (loosen the profit rules when found).
# Searches with alert_under ignore this.
# ---------------------------------------------------------------
RARE_WORDS = {
    "carhartt": ["made in usa", "usa made", "j97", "j01", "michigan", "arctic",
                 "blanket lined", "chore coat"],
    "dickies": ["made in usa", "usa made", "ike jacket"],
    "ralph_lauren": ["made in usa", "usa made", "stadium", "snow beach", "p-wing",
                     "polo bear", "hi tech", "rrl", "double rl", "purple label"],
    "mertra_tnf": ["heat reactive", "heat-reactive", "colour change", "color change"],
    "patagonia_arcteryx": ["retro-x", "retro x", "synchilla", "snap-t", "nano puff",
                           "down sweater", "made in usa", "alpha sv", "alpha ar",
                           "beta sv", "beta ar", "gore-tex pro", "gore tex pro",
                           "veilance", "made in canada"],
}


# ---------------------------------------------------------------
# SEARCHES
# _t(query, resell, channel, size_kind) works out max_buy for you.
# Extra options:
#   max_buy=N        force a buy limit
#   min_buy=N        lowest price to alert on (fake guard)
#   alert_under=N    alert for ANY listing at N pounds or less, profit rules skipped
#   no_modern=True   send nothing for modern (non-vintage) items
#   require_any=[..] listing must contain one of these words
#   items=N          how many newest listings to check for this search
# size_kind None = no size filter (kids are still blocked)
# ---------------------------------------------------------------
def _t(query, resell, channel, kind, max_buy=None, **extra):
    if max_buy is None:
        max_buy = extra.get("alert_under") or max_buy_for(resell, channel)
    d = {"query": query, "resell": resell, "max_buy": max_buy, "channel": channel, "kind": kind}
    d.update(extra)
    return d


# North Face: puffers ONLY (a listing must say one of these words)
NF_PUFFER_WORDS = ["puffer", "puffa", "puffy", "nuptse", "down", "padded", "quilted"]

TARGETS = [
    # ----- CARHARTT (resell = vintage price; modern is cut by MODERN_RESELL_FACTOR) -----
    _t("carhartt jacket", 38, "carhartt", "tops"),
    _t("carhartt detroit jacket", 38, "carhartt", "tops"),
    _t("carhartt santa fe jacket", 38, "carhartt", "tops"),
    _t("carhartt active jacket", 38, "carhartt", "tops"),
    _t("carhartt jeans", 20, "carhartt", "bottoms", alert_under=10, no_modern=True),
    _t("carhartt carpenter jeans", 20, "carhartt", "bottoms", alert_under=10, no_modern=True),
    _t("carhartt tee", 17, "carhartt", "tops"),
    _t("carhartt vintage coat", 25, "carhartt", "tops"),
    _t("carhartt double knee pants", 27, "carhartt", "bottoms"),
    _t("carhartt single knee pants", 21, "carhartt", "bottoms"),

    # ----- DICKIES (about 10 percent lower than Carhartt across the board) -----
    _t("dickies eisenhower jacket", 34, "dickies", "tops"),
    _t("dickies duck jacket", 34, "dickies", "tops"),
    _t("dickies jeans", 18, "dickies", "bottoms", alert_under=9, no_modern=True),
    _t("dickies carpenter jeans", 18, "dickies", "bottoms", alert_under=9, no_modern=True),

    # ----- RALPH LAUREN (plain polo at 7 can never profit, so no search) -----
    _t("ralph lauren big pony polo", 18, "ralph_lauren", "tops"),
    _t("ralph lauren bear jumper", 35, "ralph_lauren", "tops"),
    _t("ralph lauren knit", 20, "ralph_lauren", "tops"),
    _t("ralph lauren cable knit jumper", 20, "ralph_lauren", "tops"),
    _t("ralph lauren rugby shirt", 30, "ralph_lauren", "tops", max_buy=10),
    _t("ralph lauren quarter zip", 26, "ralph_lauren", "tops", max_buy=7),
    _t("ralph lauren harrington jacket", 42, "ralph_lauren", "tops", max_buy=20),

    # ----- THE NORTH FACE: PUFFERS ONLY, resell 40, alert at 22 pounds or less -----
    _t("north face puffer jacket", 40, "mertra_tnf", "tops", alert_under=22, require_any=NF_PUFFER_WORDS),
    _t("north face nuptse", 40, "mertra_tnf", "tops", alert_under=22, require_any=NF_PUFFER_WORDS),
    _t("north face down jacket", 40, "mertra_tnf", "tops", alert_under=22, require_any=NF_PUFFER_WORDS),

    # ----- MERTRA: loose standards, ALL sizes (kids still blocked), bigger scans -----
    _t("mertra", 45, "mertra_tnf", None, alert_under=30, items=30),
    _t("mertra jacket", 55, "mertra_tnf", None, alert_under=40, items=30),
    _t("mertra hoodie", 45, "mertra_tnf", None, alert_under=30, items=30),
    _t("mertra puffer", 70, "mertra_tnf", None, alert_under=55, items=30),
    _t("mertra heat reactive puffer", 85, "mertra_tnf", None, alert_under=65, items=30),
    _t("mertra windbreaker", 50, "mertra_tnf", None, alert_under=35, items=30),
    _t("mertra shell jacket", 50, "mertra_tnf", None, alert_under=35, items=30),

    # ----- PATAGONIA (placeholder prices: replace with your real sold prices) -----
    _t("patagonia fleece", 40, "patagonia_arcteryx", "tops", min_buy=8),
    _t("patagonia synchilla", 50, "patagonia_arcteryx", "tops", min_buy=8),
    _t("patagonia retro x", 60, "patagonia_arcteryx", "tops", min_buy=8),
    _t("patagonia better sweater", 40, "patagonia_arcteryx", "tops", min_buy=8),
    _t("patagonia nano puff", 60, "patagonia_arcteryx", "tops", min_buy=8),
    _t("patagonia down sweater", 70, "patagonia_arcteryx", "tops", min_buy=8),
    _t("patagonia torrentshell", 40, "patagonia_arcteryx", "tops", min_buy=8),
    _t("patagonia jacket", 45, "patagonia_arcteryx", "tops", min_buy=8),

    # ----- ARC'TERYX (higher floor: a real one is rarely this cheap) -----
    _t("arcteryx jacket", 90, "patagonia_arcteryx", "tops", min_buy=25),
    _t("arcteryx beta jacket", 110, "patagonia_arcteryx", "tops", min_buy=25),
    _t("arcteryx atom jacket", 90, "patagonia_arcteryx", "tops", min_buy=25),
    _t("arcteryx gore tex jacket", 100, "patagonia_arcteryx", "tops", min_buy=25),
    _t("arcteryx fleece", 50, "patagonia_arcteryx", "tops", min_buy=15),
]

# ---------------------------------------------------------------
# MISSPELLING HUNTER
# (channel, misspellings, [(product word, size kind, resell, optional extras)])
# The listing TITLE must contain the misspelling to count.
# ---------------------------------------------------------------
MISSPELL_PLAN = [
    ("carhartt", ["carhart", "carharrt", "carhatt"],
     [("jacket", "tops", 38),
      ("jeans", "bottoms", 20, {"alert_under": 10, "no_modern": True})]),
    ("dickies", ["dickie", "dickeys"],
     [("jacket", "tops", 34)]),
    ("ralph_lauren", ["ralf lauren", "ralph laren", "ralph lauran"],
     [("jumper", "tops", 20)]),
    ("mertra_tnf", ["northface", "tnf"],
     [("puffer", "tops", 40, {"alert_under": 22, "require_any": NF_PUFFER_WORDS})]),
    ("mertra_tnf", ["mertrra", "meertra"],
     [("puffer", None, 70, {"alert_under": 55, "items": 30})]),
    ("patagonia_arcteryx", ["patagonya", "patagoina", "patogonia"],
     [("fleece", "tops", 40, {"min_buy": 8})]),
    ("patagonia_arcteryx", ["arcterix", "arcteryk", "arc teryx"],
     [("jacket", "tops", 90, {"min_buy": 25})]),
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
