import os

# ---------------------------------------------------------------
# WEBHOOKS: which GitHub Secret feeds which Discord channel
# ---------------------------------------------------------------
WEBHOOK_SECRETS = {
    "carhartt": "DISCORD_WEBHOOK_CARHARTT",
    "dickies": "DISCORD_WEBHOOK_CARHARTT",
    "ralph_lauren": "DISCORD_WEBHOOK_RALPHLAUREN",
}


def get_webhook(channel):
    return os.environ.get(WEBHOOK_SECRETS.get(channel, ""))


ENABLED_CHANNELS = {"carhartt", "dickies", "ralph_lauren"}

# Which channel receives the once-a-day summary message
SUMMARY_CHANNEL = "carhartt"

# ---------------------------------------------------------------
# MONEY RULES
# ---------------------------------------------------------------
MIN_BUY_PRICE = 5.0
MIN_NET_PROFIT = 12.0      # profit AFTER fees + postage
MIN_ROI = 1.0              # profit must be at least 100% of buy price
RESELL_FEE_PCT = 0.128     # set 0.0 if you resell on Vinted
POSTAGE_COST = 2.50

# Looser rules when a RARE keyword is found (see RARE_WORDS)
RARE_MIN_NET_PROFIT = 8.0
RARE_MIN_ROI = 0.6
RARE_MAX_BUY_MULTIPLIER = 1.3   # allowed to pay 30 percent more for rare finds

ITEMS_PER_SEARCH = 10
MAX_ALERTS_PER_RUN = 5

# ---------------------------------------------------------------
# NEW FILTER 1: BRAND CHECK
# The brand name must appear in the title, description or brand field.
# Stops Vinted's fuzzy search sending you random other brands.
# (Not applied to misspelling searches - they have their own check.)
# ---------------------------------------------------------------
BRAND_CHECK_ENABLED = True
BRAND_WORDS = {
    "carhartt": ["carhartt", "carhart"],
    "dickies": ["dickies", "dickie"],
    "ralph_lauren": ["ralph lauren", "ralph", "polo"],
}

# ---------------------------------------------------------------
# NEW FILTER 2: CONDITION RED FLAGS
# Skips listings that mention these problems. "no holes", "without
# stains" etc. are understood and NOT counted as a problem.
# ---------------------------------------------------------------
CONDITION_CHECK_ENABLED = True
RED_FLAG_WORDS = [
    "hole", "holes", "ripped", "rip", "rips", "torn", "tear", "tears",
    "bobbling", "pilling", "pilled", "smell", "smells", "smelly", "odour", "odor",
    "mould", "mildew", "paint", "bleach", "bleached", "missing", "broken",
    "needs repair", "needs repairing", "sold as seen", "as is", "tatty", "scruffy",
]

# ---------------------------------------------------------------
# SELLER FILTERS
# (rating filter only works if Vinted provides rating data; the run
#  summary tells you whether it did)
# ---------------------------------------------------------------
BLOCKED_SELLERS = []            # usernames to always ignore, e.g. ["someuser"]
MIN_SELLER_REPUTATION = 0.8     # 0 to 1 (0.8 = 80 percent positive)
MIN_FEEDBACK_FOR_CHECK = 3      # ignore rating if seller has fewer reviews

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
    "ralph_lauren": ["faded"],
}

# Checked against TITLE and SIZE only
KIDS_WORDS = [
    "kids", "kid", "boy", "boys", "girl", "girls", "child", "children", "childrens",
    "youth", "junior", "juniors", "toddler", "baby", "infant",
]

CHECKLISTS = {
    "carhartt": "Check back patch and pocket tag, zip brand (YKK/Ideal), wash tag and stitching",
    "dickies": "Check logo quality, wash tag, stitching, hardware and zip",
    "ralph_lauren": "Check pony stitching and tag, RN number / care tag, vintage label era",
}

# ---------------------------------------------------------------
# UPGRADE 1: MODEL TIERS
# If a title contains one of the words, these prices REPLACE the
# search's own resell/max_buy. Highest resell wins if several match.
# These numbers are GUESSES - put in what YOU really get.
# ---------------------------------------------------------------
MODEL_TIERS = {
    "carhartt": [
        {"words": ["detroit"], "resell": 55, "max_buy": 28},
        {"words": ["arctic"], "resell": 60, "max_buy": 30},
        {"words": ["chore coat", "michigan"], "resell": 50, "max_buy": 25},
        {"words": ["santa fe"], "resell": 50, "max_buy": 25},
        {"words": ["double knee"], "resell": 40, "max_buy": 19},
    ],
    "dickies": [
        {"words": ["eisenhower"], "resell": 38, "max_buy": 15},
    ],
    "ralph_lauren": [
        {"words": ["polo sport"], "resell": 45, "max_buy": 20},
        {"words": ["rugby"], "resell": 38, "max_buy": 15},
        {"words": ["harrington"], "resell": 48, "max_buy": 22},
        {"words": ["purple label", "double rl", "rrl"], "resell": 80, "max_buy": 40},
    ],
}

# ---------------------------------------------------------------
# UPGRADE 2: RARE KEYWORDS (loosen the profit rules when found)
# Checked in title AND description
# ---------------------------------------------------------------
RARE_WORDS = {
    "carhartt": ["made in usa", "usa made", "j97", "j01", "michigan", "arctic",
                 "blanket lined", "chore coat"],
    "dickies": ["made in usa", "usa made", "ike jacket"],
    "ralph_lauren": ["made in usa", "usa made", "stadium", "snow beach", "p-wing",
                     "polo bear", "hi tech", "rrl", "double rl", "purple label"],
}

# ---------------------------------------------------------------
# BASE SEARCHES
# resell = CONSERVATIVE price a weak seller realistically gets
# ---------------------------------------------------------------
TARGETS = [
    {"query": "carhartt jacket", "resell": 32, "max_buy": 14, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt detroit jacket", "resell": 50, "max_buy": 25, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt santa fe jacket", "resell": 45, "max_buy": 22, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt active jacket", "resell": 38, "max_buy": 17, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt vintage coat", "resell": 35, "max_buy": 15, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt double knee pants", "resell": 38, "max_buy": 17, "channel": "carhartt", "kind": "bottoms"},
    {"query": "carhartt single knee pants", "resell": 30, "max_buy": 10, "channel": "carhartt", "kind": "bottoms"},
    {"query": "carhartt carpenter jeans", "resell": 28, "max_buy": 8, "channel": "carhartt", "kind": "bottoms"},
    {"query": "dickies eisenhower jacket", "resell": 32, "max_buy": 12, "channel": "dickies", "kind": "tops"},
    {"query": "dickies duck jacket", "resell": 28, "max_buy": 8, "channel": "dickies", "kind": "tops"},
    {"query": "polo sport ralph lauren", "resell": 35, "max_buy": 14, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren rugby shirt", "resell": 30, "max_buy": 10, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren quarter zip", "resell": 26, "max_buy": 7, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren cable knit jumper", "resell": 32, "max_buy": 12, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren harrington jacket", "resell": 42, "max_buy": 20, "channel": "ralph_lauren", "kind": "tops"},
]

# ---------------------------------------------------------------
# UPGRADE 3: MISSPELLING HUNTER
# (channel, misspellings, [(product word, size kind, resell, max_buy)])
# The listing TITLE must contain the misspelling to count.
# ---------------------------------------------------------------
MISSPELL_PLAN = [
    ("carhartt", ["carhart", "carharrt", "carhatt"],
     [("jacket", "tops", 32, 14), ("pants", "bottoms", 30, 10)]),
    ("dickies", ["dickie", "dickeys"],
     [("jacket", "tops", 28, 8)]),
    ("ralph_lauren", ["ralf lauren", "ralph laren", "ralph lauran"],
     [("jumper", "tops", 32, 12)]),
]


def _misspelled_targets():
    out = []
    for channel, spellings, products in MISSPELL_PLAN:
        for sp in spellings:
            for word, kind, resell, max_buy in products:
                out.append({
                    "query": sp + " " + word,
                    "resell": resell,
                    "max_buy": max_buy,
                    "channel": channel,
                    "kind": kind,
                    "must_match": [sp],
                    "misspelled": True,
                })
    return out


TARGETS = TARGETS + _misspelled_targets()
