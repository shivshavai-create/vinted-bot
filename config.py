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
    "stussy_supreme": "• HIGH FAKE RISK: check neck tag & wash tag
