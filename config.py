import os

# Maps each channel to the GitHub Secret holding its webhook
WEBHOOK_SECRETS = {
    "carhartt": "DISCORD_WEBHOOK_CARHARTT",
    "dickies": "DISCORD_WEBHOOK_CARHARTT",
    "ralph_lauren": "DISCORD_WEBHOOK_RALPHLAUREN",
}


def get_webhook(channel):
    return os.environ.get(WEBHOOK_SECRETS.get(channel, ""))


ENABLED_CHANNELS = {"carhartt", "dickies", "ralph_lauren"}

MIN_BUY_PRICE = 5.0
MIN_NET_PROFIT = 12.0
MIN_ROI = 1.0
RESELL_FEE_PCT = 0.128
POSTAGE_COST = 2.50

ITEMS_PER_SEARCH = 10
MAX_ALERTS_PER_RUN = 5

TOPS = {"m", "medium", "l", "large", "xl"}
BOTTOM_RANGE = (28, 38)
SHOE_RANGE = (7, 11)

BANNED_WORDS = [
    "realtree", "style", "styled", "inspired", "type",
    "rep", "reps", "replica", "fake", "unbranded", "pandabuy", "taobao", "dhgate",
    "shorts", "satisfactory", "damaged", "flawed", "stained",
]
BANNED_PHRASES = ["camo tree", "fair condition", "heavy wear", "spare or repair"]

# Extra banned words for ONE channel only (faded is fine for workwear, not for Ralph Lauren)
EXTRA_BANNED_BY_CHANNEL = {
    "ralph_lauren": ["faded"],
}

# Kids filter: checked against the TITLE and SIZE only
KIDS_WORDS = [
    "kids", "kid", "boy", "boys", "girl", "girls", "child", "children", "childrens",
    "youth", "junior", "juniors", "toddler", "baby", "infant",
]

CHECKLISTS = {
    "carhartt": "Check back patch and pocket tag, zip brand (YKK/Ideal), wash tag and stitching",
    "dickies": "Check logo quality, wash tag, stitching, hardware and zip",
    "ralph_lauren": "Check pony stitching and tag, RN number / care tag, vintage label era",
}

# resell = CONSERVATIVE price a weak seller realistically gets
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
