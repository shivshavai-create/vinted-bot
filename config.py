import os

# Maps each channel to the GitHub Secret holding its webhook
WEBHOOK_SECRETS = {
    "carhartt": "DISCORD_WEBHOOK_CARHARTT",
    "dickies": "DISCORD_WEBHOOK_CARHARTT",  # Dickies shares the Carhartt channel
    "ralph_lauren": "DISCORD_WEBHOOK_RALPHLAUREN",
}


def get_webhook(channel):
    return os.environ.get(WEBHOOK_SECRETS.get(channel, ""))


# Switch channels on/off here
ENABLED_CHANNELS = {"carhartt", "dickies", "ralph_lauren"}

# 💰 Strict money rules
MIN_BUY_PRICE = 5.0
MIN_NET_PROFIT = 12.0     # profit AFTER fees + postage
MIN_ROI = 1.0             # profit must be at least 100% of buy price
RESELL_FEE_PCT = 0.128    # set 0.0 if you resell on Vinted
POSTAGE_COST = 3.50

# 🔇 Anti-spam
ITEMS_PER_SEARCH = 10
MAX_ALERTS_PER_RUN = 5
BASELINE_FIRST_RUN = True  # first run learns existing listings, sends nothing

# Sizes
TOPS = {"m", "medium", "l", "large", "xl"}
BOTTOM_RANGE = (28, 38)
SHOE_RANGE = (7, 11)

BANNED_WORDS = [
    "realtree", "style", "styled", "inspired", "type",
    "rep", "reps", "replica", "fake", "unbranded", "pandabuy", "taobao", "dhgate",
    "shorts", "satisfactory", "damaged", "flawed", "stained", "faded",
]
BANNED_PHRASES = ["camo tree", "fair condition", "heavy wear", "spare or repair"]

CHECKLISTS = {
    "carhartt": "• Check back patch & pocket tag\n• Check zipper brand (YKK/Ideal) & button stamps\n• Check wash tag & stitching",
    "dickies": "• Check embroidered/woven logo quality\n• Check wash tag & stitching\n• Check hardware & zip",
    "nike_adidas": "• Check tag font, size tag & style code (search it!)\n• Check stitching on logo\n• Shoes: box label, insole print, smell/glue mess",
    "stussy_supreme": "• HIGH FAKE RISK: check neck tag & wash tag fonts\n• Check logo embroidery spacing\n• Ask for tag photos before buying",
    "ralph_lauren": "• Check pony stitching & tag\n• Check RN number / care tag\n• Vintage: check country of origin & label era",
}

# "resell" = CONSERVATIVE price a weak seller realistically gets.
# Replace with YOUR real sold prices when you have them!
TARGETS = [
    # CARHARTT
    {"query": "carhartt jacket", "resell": 32, "max_buy": 14, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt detroit jacket", "resell": 50, "max_buy": 25, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt santa fe jacket", "resell": 45, "max_buy": 22, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt active jacket", "resell": 38, "max_buy": 17, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt vintage coat", "resell": 35, "max_buy": 15, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt double knee pants", "resell": 38, "max_buy": 17, "channel": "carhartt", "kind": "bottoms"},
    {"query": "carhartt single knee pants", "resell": 30, "max_buy": 10, "channel": "carhartt", "kind": "bottoms"},
    {"query": "carhartt carpenter jeans", "resell": 28, "max_buy": 8, "channel": "carhartt", "kind": "bottoms"},

    # DICKIES
    {"query": "dickies eisenhower jacket", "resell": 32, "max_buy": 12, "channel": "dickies", "kind": "tops"},
    {"query": "dickies duck jacket", "resell": 28, "max_buy": 8, "channel": "dickies", "kind": "tops"},

    # NIKE / ADIDAS (off for now)
    {"query": "nike tech fleece", "resell": 35, "max_buy": 11, "channel": "nike_adidas", "kind": "tops"},
    {"query": "nike windrunner jacket", "resell": 28, "max_buy": 8, "channel": "nike_adidas", "kind": "tops"},
    {"query": "nike vintage sweatshirt", "resell": 26, "max_buy": 7, "channel": "nike_adidas", "kind": "tops"},
    {"query": "nike air max 95", "resell": 60, "max_buy": 35, "channel": "nike_adidas", "kind": "shoes"},
    {"query": "adidas samba", "resell": 48, "max_buy": 26, "channel": "nike_adidas", "kind": "shoes"},

    # STUSSY / SUPREME (off for now)
    {"query": "stussy hoodie", "resell": 40, "max_buy": 19, "min_buy": 12, "channel": "stussy_supreme", "kind": "tops"},
    {"query": "stussy sweatshirt", "resell": 36, "max_buy": 15, "min_buy": 12, "channel": "stussy_supreme", "kind": "tops"},
    {"query": "supreme hoodie", "resell": 75, "max_buy": 45, "min_buy": 30, "channel": "stussy_supreme", "kind": "tops"},
    {"query": "supreme jacket", "resell": 85, "max_buy": 50, "min_buy": 30, "channel": "stussy_supreme", "kind": "tops"},

    # RALPH LAUREN
    {"query": "polo sport ralph lauren", "resell": 35, "max_buy": 14, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren rugby shirt", "resell": 30, "max_buy": 10, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren quarter zip", "resell": 26, "max_buy": 7, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren cable knit jumper", "resell": 32, "max_buy": 12, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren harrington jacket", "resell": 42, "max_buy": 20, "channel": "ralph_lauren", "kind": "tops"},
]
