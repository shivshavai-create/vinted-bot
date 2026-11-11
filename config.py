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
    "nike_adidas": "DISCORD_WEBHOOK_NIKE",
}


def get_webhook(channel):
    return os.environ.get(WEBHOOK_SECRETS.get(channel, ""))


ENABLED_CHANNELS = {"carhartt", "dickies", "ralph_lauren", "stussy_supreme", "nike_adidas"}

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

# Stricter rules for specific channels (Nike/Adidas = no selling history, so brutal)
ROI_BY_CHANNEL = {"nike_adidas": 1.5}
MIN_PROFIT_BY_CHANNEL = {"nike_adidas": 10.0}

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
    "nike_adidas": ["nike", "adidas"],
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

EXTRA_BANNED_BY_CHANNEL = {
    "ralph_lauren": ["faded"],
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
    "nike_adidas": "Check vintage tag era, stitching on logo, size tag and country of origin",
}

# ---------------------------------------------------------------
# MODEL TIERS: a model word in the title can RAISE the resell price
# (never lowers it). max_buy is worked out automatically.
# ---------------------------------------------------------------
MODEL_TIERS = {
    "carhartt": [
        {"words": ["detroit"], "resell": 55},
        {"words": ["arctic"], "resell": 60},
        {"words": ["chore coat", "michigan"], "resell": 50},
        {"words": ["santa fe"], "resell": 50},
        {"words": ["double knee"], "resell": 40},
    ],
    "dickies": [
        {"words": ["eisenhower"], "resell": 38},
    ],
    "ralph_lauren": [
        {"words": ["polo sport"], "resell": 45},
        {"words": ["rugby"], "resell": 38},
        {"words": ["harrington"], "resell": 48},
        {"words": ["bear"], "resell": 35},
        {"words": ["purple label", "double rl", "rrl"], "resell": 80},
    ],
}

# ---------------------------------------------------------------
# RARE KEYWORDS (loosen the profit rules when found).
# Left empty for stussy_supreme (fake risk) and nike_adidas (brutal mode).
# ---------------------------------------------------------------
RARE_WORDS = {
    "carhartt": ["made in usa", "usa made", "j97", "j01", "michigan", "arctic",
                 "blanket lined", "chore coat"],
    "dickies": ["made in usa", "usa made", "ike jacket"],
    "ralph_lauren": ["made in usa", "usa made", "stadium", "snow beach", "p-wing",
                     "polo bear", "hi tech", "rrl", "double rl", "purple label"],
}


# ---------------------------------------------------------------
# SEARCHES
# _t(query, resell, channel, size_kind) works out max_buy for you.
# Pass max_buy=... to force a number (used to keep your old vintage prices).
# ---------------------------------------------------------------
def _t(query, resell, channel, kind, max_buy=None, **extra):
    if max_buy is None:
        max_buy = max_buy_for(resell, channel)
    d = {"query": query, "resell": resell, "max_buy": max_buy, "channel": channel, "kind": kind}
    d.update(extra)
    return d


# Nike/Adidas: vintage only (listing must say one of these words)
VINTAGE_WORDS = ["vintage", "90s", "80s", "70s"]

TARGETS = [
    # ----- CARHARTT (your prices) -----
    _t("carhartt jacket", 60, "carhartt", "tops"),
    _t("carhartt detroit jacket", 60, "carhartt", "tops"),
    _t("carhartt santa fe jacket", 60, "carhartt", "tops"),
    _t("carhartt active jacket", 60, "carhartt", "tops"),
    _t("carhartt jeans", 20, "carhartt", "bottoms"),
    _t("carhartt carpenter jeans", 20, "carhartt", "bottoms"),
    _t("carhartt tee", 17, "carhartt", "tops"),
    # vintage / unchanged normal prices
    _t("carhartt vintage coat", 35, "carhartt", "tops", max_buy=15),
    _t("carhartt double knee pants", 38, "carhartt", "bottoms", max_buy=17),
    _t("carhartt single knee pants", 30, "carhartt", "bottoms", max_buy=10),

    # ----- DICKIES -----
    _t("dickies eisenhower jacket", 60, "dickies", "tops"),
    _t("dickies duck jacket", 60, "dickies", "tops"),
    _t("dickies jeans", 20, "dickies", "bottoms"),
    _t("dickies carpenter jeans", 20, "dickies", "bottoms"),

    # ----- RALPH LAUREN (your prices; plain polo at 7 can never profit, so no search) -----
    _t("ralph lauren big pony polo", 18, "ralph_lauren", "tops"),
    _t("ralph lauren bear jumper", 35, "ralph_lauren", "tops"),
    _t("ralph lauren knit", 20, "ralph_lauren", "tops"),
    _t("ralph lauren cable knit jumper", 20, "ralph_lauren", "tops"),
    # vintage / unchanged normal prices
    _t("polo sport ralph lauren", 35, "ralph_lauren", "tops", max_buy=14),
    _t("ralph lauren rugby shirt", 30, "ralph_lauren", "tops", max_buy=10),
    _t("ralph lauren quarter zip", 26, "ralph_lauren", "tops", max_buy=7),
    _t("ralph lauren harrington jacket", 42, "ralph_lauren", "tops", max_buy=20),

    # ----- STUSSY / SUPREME (your prices) -----
    _t("stussy tee", 20, "stussy_supreme", "tops"),
    _t("supreme tee", 25, "stussy_supreme", "tops"),
    _t("stussy hoodie", 30, "stussy_supreme", "tops"),
    _t("supreme hoodie", 40, "stussy_supreme", "tops"),

    # ----- NIKE / ADIDAS: VINTAGE ONLY, BRUTAL PRICES -----
    _t("vintage nike sweatshirt", 22, "nike_adidas", "tops", require_any=VINTAGE_WORDS),
    _t("vintage nike jacket", 28, "nike_adidas", "tops", require_any=VINTAGE_WORDS),
    _t("vintage nike track jacket", 25, "nike_adidas", "tops", require_any=VINTAGE_WORDS),
    _t("vintage nike fleece", 22, "nike_adidas", "tops", require_any=VINTAGE_WORDS),
    _t("vintage adidas track top", 22, "nike_adidas", "tops", require_any=VINTAGE_WORDS),
    _t("vintage adidas jacket", 25, "nike_adidas", "tops", require_any=VINTAGE_WORDS),
]

# ---------------------------------------------------------------
# MISSPELLING HUNTER
# (channel, misspellings, [(product word, size kind, resell)])
# The listing TITLE must contain the misspelling to count.
# ---------------------------------------------------------------
MISSPELL_PLAN = [
    ("carhartt", ["carhart", "carharrt", "carhatt"],
     [("jacket", "tops", 60), ("jeans", "bottoms", 20)]),
    ("dickies", ["dickie", "dickeys"],
     [("jacket", "tops", 60)]),
    ("ralph_lauren", ["ralf lauren", "ralph laren", "ralph lauran"],
     [("jumper", "tops", 20)]),
    ("stussy_supreme", ["stusy", "stussi"],
     [("hoodie", "tops", 30)]),
    ("stussy_supreme", ["supreem", "suprame"],
     [("hoodie", "tops", 40)]),
]


def _misspelled_targets():
    out = []
    for channel, spellings, products in MISSPELL_PLAN:
        for sp in spellings:
            for word, kind, resell in products:
                out.append(_t(sp + " " + word, resell, channel, kind,
                              must_match=[sp], misspelled=True))
    return out


TARGETS = TARGETS + _misspelled_targets()
