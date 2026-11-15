import math
import os

# ---------------------------------------------------------------
# WEBHOOKS: which GitHub Secret feeds which Discord channel
# ---------------------------------------------------------------
WEBHOOK_SECRETS = {
    "carhartt": "DISCORD_WEBHOOK_CARHARTT",
    "dickies": "DISCORD_WEBHOOK_CARHARTT",
    "ralph_lauren": "DISCORD_WEBHOOK_RALPHLAUREN",
    "stussy_supreme": "DISCORD_WEBHOOK_STUSSY",
    "mertra_tnf": "DISCORD_WEBHOOK_MERTRA",
}


def get_webhook(channel):
    return os.environ.get(WEBHOOK_SECRETS.get(channel, ""))


ENABLED_CHANNELS = {"carhartt", "dickies", "ralph_lauren", "stussy_supreme", "mertra_tnf"}

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

# Optional stricter rules for one channel, e.g. {"stussy_supreme": 1.5}
ROI_BY_CHANNEL = {}
MIN_PROFIT_BY_CHANNEL = {}

# Looser rules when a RARE keyword is found (see RARE_WORDS)
RARE_MIN_NET_PROFIT = 4.0
RARE_MIN_ROI = 0.6
RARE_MAX_BUY_MULTIPLIER = 1.3   # allowed to pay 30 percent more for rare finds

ITEMS_PER_SEARCH = 10
MAX_ALERTS_PER_RUN = 5

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
    "stussy_supreme": ["stussy", "st\u00fcssy", "supreme"],
    "mertra_tnf": ["mertra", "north face", "northface", "tnf"],
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
BANNED_PHRASES = ["camo tree", "fair condition", "heavy wear", "spare or repair"]

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
    "stussy_supreme": "HIGH FAKE RISK: check neck tag and wash tag fonts, logo stitching, ask for tag photos before buying",
    "mertra_tnf": "Fakes exist for both brands: check logo stitching, YKK zips, labels and RN/fill tags, ask for tag photos",
}

# ---------------------------------------------------------------
# MODEL TIERS: a model word in the title can RAISE the resell price
# (never lowers it). max_buy is worked out automatically.
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
}

# ---------------------------------------------------------------
# RARE KEYWORDS (loosen the profit rules when found).
# Left empty for stussy_supreme because of fake risk.
# (Searches with alert_under ignore the rare boost.)
# ---------------------------------------------------------------
RARE_WORDS = {
    "carhartt": ["made in usa", "usa made", "j97", "j01", "michigan", "arctic",
                 "blanket lined", "chore coat"],
    "dickies": ["made in usa", "usa made", "ike jacket"],
    "ralph_lauren": ["made in usa", "usa made", "stadium", "snow beach", "p-wing",
                     "polo bear", "hi tech", "rrl", "double rl", "purple label"],
    "mertra_tnf": ["heat reactive", "heat-reactive", "colour change", "color change"],
}


# ---------------------------------------------------------------
# SEARCHES
# _t(query, resell, channel, size_kind) works out max_buy for you.
# Extra options:
#   max_buy=N        force a buy limit
#   alert_under=N    alert for ANY listing at N pounds or less, profit rules skipped
#   no_modern=True   send nothing for modern (non-vintage) items
# ---------------------------------------------------------------
def _t(query, resell, channel, kind, max_buy=None, **extra):
    if max_buy is None:
        max_buy = extra.get("alert_under") or max_buy_for(resell, channel)
    d = {"query": query, "resell": resell, "max_buy": max_buy, "channel": channel, "kind": kind}
    d.update(extra)
    return d


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

    # ----- STUSSY / SUPREME -----
    _t("stussy tee", 20, "stussy_supreme", "tops"),
    _t("supreme tee", 25, "stussy_supreme", "tops"),
    _t("stussy hoodie", 30, "stussy_supreme", "tops"),
    _t("supreme hoodie", 40, "stussy_supreme", "tops"),

    # ----- THE NORTH FACE: resell 40, alert for ANYTHING at 22 pounds or less -----
    _t("north face puffer jacket", 40, "mertra_tnf", "tops", alert_under=22),
    _t("north face nuptse", 40, "mertra_tnf", "tops", alert_under=22),
    _t("north face down jacket", 40, "mertra_tnf", "tops", alert_under=22),
    _t("north face windbreaker", 40, "mertra_tnf", "tops", alert_under=22),
    _t("north face shell jacket", 40, "mertra_tnf", "tops", alert_under=22),

    # ----- MERTRA -----
    # Puffers: alert for ANYTHING at 55 pounds or less (profit rules skipped)
    _t("mertra puffer", 70, "mertra_tnf", "tops", alert_under=55),
    _t("mertra heat reactive puffer", 85, "mertra_tnf", "tops", alert_under=55),
    # Windbreakers / shells: normal profit rules
    _t("mertra windbreaker", 50, "mertra_tnf", "tops"),
    _t("mertra shell jacket", 50, "mertra_tnf", "tops"),
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
    ("stussy_supreme", ["stusy", "stussi"],
     [("hoodie", "tops", 30)]),
    ("stussy_supreme", ["supreem", "suprame"],
     [("hoodie", "tops", 40)]),
    ("mertra_tnf", ["northface", "tnf"],
     [("puffer", "tops", 40, {"alert_under": 22}),
      ("windbreaker", "tops", 40, {"alert_under": 22})]),
    ("mertra_tnf", ["mertrra", "meertra"],
     [("puffer", "tops", 70, {"alert_under": 55})]),
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
