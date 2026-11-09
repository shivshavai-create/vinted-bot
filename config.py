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

# Money rules
MIN_BUY_PRICE = 6.0
MIN_NET_PROFIT = 10.0
RESELL_FEE_PCT = 0.128   # set 0.0 if you resell on Vinted
POSTAGE_COST = 3.50
ITEMS_PER_SEARCH = 20

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

# Resell prices for new brands are PLACEHOLDERS: verify on eBay sold listings!
TARGETS = [
    # CARHARTT
    {"query": "carhartt jacket", "resell": 45, "max_buy": 25, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt detroit jacket", "resell": 70, "max_buy": 45, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt santa fe jacket", "resell": 65, "max_buy": 40, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt active jacket", "resell": 55, "max_buy": 32, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt vintage coat", "resell": 50, "max_buy": 30, "channel": "carhartt", "kind": "tops"},
    {"query": "carhartt double knee pants", "resell": 55, "max_buy": 32, "channel": "carhartt", "kind": "bottoms"},
    {"query": "carhartt single knee pants", "resell": 45, "max_buy": 25, "channel": "carhartt", "kind": "bottoms"},
    {"query": "carhartt denim jeans", "resell": 35, "max_buy": 18, "channel": "carhartt", "kind": "bottoms"},
    {"query": "carhartt carpenter jeans", "resell": 40, "max_buy": 22, "channel": "carhartt", "kind": "bottoms"},

    # DICKIES
    {"query": "dickies eisenhower jacket", "resell": 45, "max_buy": 25, "channel": "dickies", "kind": "tops"},
    {"query": "dickies duck jacket", "resell": 40, "max_buy": 22, "channel": "dickies", "kind": "tops"},
    {"query": "dickies vintage jacket", "resell": 35, "max_buy": 18, "channel": "dickies", "kind": "tops"},
    {"query": "dickies double knee pants", "resell": 35, "max_buy": 18, "channel": "dickies", "kind": "bottoms"},
    {"query": "dickies carpenter jeans", "resell": 30, "max_buy": 15, "channel": "dickies", "kind": "bottoms"},
    {"query": "dickies denim jeans", "resell": 28, "max_buy": 14, "channel": "dickies", "kind": "bottoms"},

    # NIKE / ADIDAS (off for now)
    {"query": "nike tech fleece", "resell": 45, "max_buy": 22, "channel": "nike_adidas", "kind": "tops"},
    {"query": "nike windrunner jacket", "resell": 38, "max_buy": 16, "channel": "nike_adidas", "kind": "tops"},
    {"query": "nike vintage sweatshirt", "resell": 35, "max_buy": 15, "channel": "nike_adidas", "kind": "tops"},
    {"query": "adidas track top", "resell": 30, "max_buy": 13, "channel": "nike_adidas", "kind": "tops"},
    {"query": "nike air max 95", "resell": 75, "max_buy": 40, "channel": "nike_adidas", "kind": "shoes"},
    {"query": "adidas samba", "resell": 60, "max_buy": 32, "channel": "nike_adidas", "kind": "shoes"},

    # STUSSY / SUPREME (off for now)
    {"query": "stussy hoodie", "resell": 50, "max_buy": 25, "min_buy": 12, "channel": "stussy_supreme", "kind": "tops"},
    {"query": "stussy sweatshirt", "resell": 45, "max_buy": 22, "min_buy": 12, "channel": "stussy_supreme", "kind": "tops"},
    {"query": "supreme hoodie", "resell": 95, "max_buy": 55, "min_buy": 30, "channel": "stussy_supreme", "kind": "tops"},
    {"query": "supreme jacket", "resell": 110, "max_buy": 60, "min_buy": 30, "channel": "stussy_supreme", "kind": "tops"},

    # RALPH LAUREN
    {"query": "polo sport ralph lauren", "resell": 45, "max_buy": 22, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren rugby shirt", "resell": 40, "max_buy": 18, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren quarter zip", "resell": 35, "max_buy": 15, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren cable knit jumper", "resell": 42, "max_buy": 18, "channel": "ralph_lauren", "kind": "tops"},
    {"query": "ralph lauren harrington jacket", "resell": 55, "max_buy": 28, "channel": "ralph_lauren", "kind": "tops"},
]
