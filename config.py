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
    "cameras": "DISCORD_WEBHOOK_PATAGONIA",      # same webhook the Patagonia channel used
}


def get_webhook(channel):
    return os.environ.get(WEBHOOK_SECRETS.get(channel, ""))


ENABLED_CHANNELS = {"carhartt", "dickies", "ralph_lauren", "mertra_tnf", "cameras"}

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

# Rules and postage for one channel (cameras cost more to post and sit at a higher price)
ROI_BY_CHANNEL = {"cameras": 0.6}              # profit must be 60 percent of the buy price
MIN_PROFIT_BY_CHANNEL = {"cameras": 12.0}
POSTAGE_BY_CHANNEL = {"cameras": 4.50}         # a single search can override with postage=N

# Looser rules when a RARE keyword is found (see RARE_WORDS)
RARE_MIN_NET_PROFIT = 4.0
RARE_MIN_ROI = 0.6
RARE_MAX_BUY_MULTIPLIER = 1.3   # allowed to pay 30 percent more for rare finds

# ---------------------------------------------------------------
# ALERT LIMITS PER RUN
# Each channel gets its own cap so one channel can never push the others out.
# ---------------------------------------------------------------
ITEMS_PER_SEARCH = 10           # a search can override this with items=N
MAX_ALERTS_PER_RUN = 14
MAX_ALERTS_PER_CHANNEL = 3
MAX_ALERTS_BY_CHANNEL = {"mertra_tnf": 5, "cameras": 5}

# ---------------------------------------------------------------
# STATE / REPEAT PROTECTION
# A listing that has been alerted is NEVER alerted again.
# The same seller + same title (a relist) is blocked too.
# ---------------------------------------------------------------
SEEN_RETENTION_DAYS = 45        # forget checked-but-not-alerted listings after this
ALERTED_ID_RETENTION_DAYS = 180
ALERTED_RELIST_RETENTION_DAYS = 60
TIME_BUDGET_SECONDS = 720       # stop searching after 12 minutes and save state

# ---------------------------------------------------------------
# AUTHENTIC / REAL CLAIMS (off for now; add a channel here to use it)
# ---------------------------------------------------------------
AUTHENTIC_BONUS_CHANNELS = set()
AUTHENTIC_WORDS = [
    "100% authentic", "100% real", "guaranteed authentic", "guaranteed real",
    "authenticated", "authentic", "genuine", "legit", "real",
]
AUTHENTIC_MAX_BUY_MULTIPLIER = 1.15
AUTHENTIC_RANK_BONUS = 10.0

# ---------------------------------------------------------------
# OFFER SUGGESTION
# Alerts show an offer price and the profit with AND without it.
# ---------------------------------------------------------------
OFFER_ENABLED = True
OFFER_PERCENT = 0.80            # offer 80 percent of the asking price
OFFER_MIN_PRICE = 6.0           # no offer suggested on very cheap items
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
    "cameras": ["canon", "nikon", "sony", "fuji", "fujifilm", "olympus", "panasonic",
                "lumix", "pentax", "ricoh", "samsung", "kodak", "casio", "minolta",
                "gopro", "cybershot", "cyber-shot", "cyber shot", "coolpix", "ixus",
                "powershot", "finepix", "digicam", "digital camera", "ccd", "contax",
                "yashica", "konica", "leica", "vivitar", "agfa", "fujica", "exilim"],
}

# ---------------------------------------------------------------
# CONDITION RED FLAGS ("no holes", "no faults", "not faulty" are understood)
# ---------------------------------------------------------------
CONDITION_CHECK_ENABLED = True
RED_FLAG_WORDS = [
    # clothing
    "hole", "holes", "ripped", "rip", "rips", "torn", "tear", "tears",
    "bobbling", "pilling", "pilled", "smell", "smells", "smelly", "odour", "odor",
    "mould", "mildew", "paint", "bleach", "bleached", "missing", "broken",
    "needs repair", "needs repairing", "sold as seen", "as is", "tatty", "scruffy",
    # cameras and electronics
    "faulty", "fault", "untested", "spares", "for parts", "for spares", "not working",
    "doesn't work", "doesnt work", "error", "fungus", "fungi", "haze", "hazy",
    "sticky", "jammed", "dead pixel", "dead pixels", "cracked",
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
    "cameras": [
        "whatsapp", "bank transfer", "paypal friends", "dummy", "toy", "prop",
        "box only", "empty box", "case only", "strap only", "manual only",
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
    "cameras": "Ask for a photo of it switched on, check the lens for fungus/scratches, battery and charger included, shutter count on DSLRs",
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
    # The most SPECIFIC matching word wins (so "mju ii zoom" beats "mju ii").
    # A tier only ever RAISES the price a search starts with.
    # Prices are conservative private-sale guesses. "(est)" = no data found, my estimate.
    "cameras": [
        # --- Canon IXUS / PowerShot digicams ---
        {"words": ["ixus 40"], "resell": 40},
        {"words": ["ixus 50", "ixus 55", "ixus 60", "ixus 65"], "resell": 55},      # (est)
        {"words": ["ixus 70", "ixus 75"], "resell": 70},
        {"words": ["ixus 80", "ixus 82", "ixus 85", "ixus 90", "ixus 95"], "resell": 65},  # (est)
        {"words": ["ixus 100", "ixus 105", "ixus 107", "ixus 115"], "resell": 70},
        {"words": ["ixus 110", "ixus 120", "ixus 130"], "resell": 85},
        {"words": ["ixus 132"], "resell": 85},
        {"words": ["ixus 145", "ixus 150", "ixus 160", "ixus 170"], "resell": 100},
        {"words": ["ixus 175", "ixus 177", "ixus 180", "ixus 185", "ixus 190"], "resell": 80},  # (est)
        {"words": ["ixus 285"], "resell": 110},                                     # (est)
        {"words": ["powershot a495", "powershot a490", "powershot a480"], "resell": 40},
        {"words": ["powershot sx", "powershot s95", "powershot s100", "powershot s110"], "resell": 110},  # (est)
        {"words": ["powershot g9", "powershot g10", "powershot g11", "powershot g12"], "resell": 130},   # (est)
        {"words": ["g7x", "g7 x"], "resell": 350},                                  # (est) original model
        {"words": ["g7x mark ii", "g7 x mark ii", "g7x ii", "g7 x ii"], "resell": 600},
        {"words": ["g7x mark iii", "g7 x mark iii", "g7x iii"], "resell": 650},     # (est)
        {"words": ["powershot g9 x", "g9x"], "resell": 300},                        # (est)
        # --- Sony Cyber-shot ---
        {"words": ["dsc-p", "dsc p"], "resell": 35},
        {"words": ["dsc-s", "dsc s"], "resell": 55},
        {"words": ["dsc-t", "dsc t"], "resell": 60},                                # (est)
        {"words": ["dsc-h", "dsc h"], "resell": 55},                                # (est)
        {"words": ["dsc-w", "dsc w"], "resell": 50},                                # (est) typical W-series
        {"words": ["dsc-w55", "dsc w55", "w55"], "resell": 65},
        {"words": ["dsc-w50", "dsc w50"], "resell": 60},
        {"words": ["dsc-w120", "dsc w120", "w120"], "resell": 45},
        {"words": ["dsc-w130", "dsc w130", "w130"], "resell": 55},
        {"words": ["dsc-w300", "dsc w300", "w300"], "resell": 90},
        {"words": ["dsc-w810", "dsc w810", "w810"], "resell": 70},
        {"words": ["dsc-s600", "dsc s600", "s600"], "resell": 70},
        {"words": ["dsc-p150", "dsc p150", "p150"], "resell": 40},
        {"words": ["dsc-hx", "dsc hx"], "resell": 80},                              # (est)
        {"words": ["hx1"], "resell": 90},
        {"words": ["rx100"], "resell": 220},                                        # Vinted ask about 290 for the first one
        {"words": ["rx100 ii", "rx100 m2", "rx100 mark 2"], "resell": 270},         # (est)
        {"words": ["rx100 iii", "rx100 m3", "rx100 mark 3"], "resell": 380},
        {"words": ["rx100 iv", "rx100 m4"], "resell": 450},                         # (est)
        {"words": ["rx100 v", "rx100 m5"], "resell": 550},
        {"words": ["sony a6000", "alpha a6000", "a6000"], "resell": 230},
        {"words": ["sony a5100", "a5100"], "resell": 170},                          # (est)
        # --- Nikon / Fuji / Olympus / Panasonic / Casio digicams ---
        {"words": ["coolpix s"], "resell": 45},                                     # (est)
        {"words": ["coolpix s4100"], "resell": 55},
        {"words": ["finepix f11", "finepix f10", "finepix f20", "finepix f30", "finepix f31"], "resell": 70},  # (est) cult F-series
        {"words": ["finepix z90", "finepix z"], "resell": 35},
        {"words": ["finepix"], "resell": 35},
        {"words": ["vg-150", "vg150"], "resell": 35},
        {"words": ["sz-20", "sz20"], "resell": 50},
        {"words": ["lumix fs18", "lumix dmc-fs18"], "resell": 45},
        {"words": ["lumix lx3", "lumix lx5", "lumix lx7"], "resell": 150},          # (est)
        {"words": ["lumix tz"], "resell": 90},                                      # (est)
        {"words": ["exilim ex-z", "exilim z"], "resell": 55},                       # (est) Y2K trend
        {"words": ["ricoh gr ii"], "resell": 450},                                  # (est)
        {"words": ["ricoh gr iii"], "resell": 700},
        {"words": ["ricoh gr iiix"], "resell": 750},                                # (est)
        # --- film compacts: the ones sellers underprice ---
        {"words": ["mju ii", "mju-ii", "mjuii", "mju 2", "stylus epic"], "resell": 170},
        {"words": ["mju ii zoom", "mju zoom", "mju-ii zoom"], "resell": 80},
        {"words": ["mju v", "mju-v", "mju 5"], "resell": 100},
        {"words": ["mju iii", "mju-iii", "mju 3", "mju iv", "mju-iv"], "resell": 90},   # (est)
        {"words": ["olympus xa"], "resell": 140},                                   # (est)
        {"words": ["olympus trip 35", "trip 35"], "resell": 90},
        {"words": ["contax t2"], "resell": 600},                                    # (est) very high value
        {"words": ["contax t3"], "resell": 900},                                    # (est)
        {"words": ["yashica t4", "yashica t5", "t4 super"], "resell": 350},         # (est)
        {"words": ["konica big mini", "big mini"], "resell": 150},                  # (est)
        {"words": ["leica mini", "leica minilux"], "resell": 120},
        {"words": ["pentax pc35", "pc35af"], "resell": 35},
        {"words": ["ricoh tf-500", "ricoh tf500"], "resell": 35},
        {"words": ["pentax espio"], "resell": 60},                                  # (est)
        {"words": ["nikon l35", "l35af"], "resell": 70},                            # (est)
        {"words": ["sure shot", "sureshot", "autoboy", "canon prima"], "resell": 45},  # (est)
        # --- film SLRs ---
        {"words": ["pentax k1000"], "resell": 100},
        {"words": ["canon ae-1", "canon ae1"], "resell": 90},                       # (est)
        {"words": ["nikon fm2"], "resell": 250},                                    # (est)
        {"words": ["nikon fm10"], "resell": 100},                                   # (est)
        # --- budget DSLRs and mirrorless ---
        {"words": ["eos 600d", "eos 1100d", "eos 1200d", "eos 1000d"], "resell": 70},   # (est)
        {"words": ["eos 700d", "eos 650d", "eos 100d"], "resell": 90},              # (est)
        {"words": ["eos 1300d"], "resell": 100},
        {"words": ["eos 2000d", "eos 4000d", "eos 750d"], "resell": 125},
        {"words": ["eos 800d", "eos 77d", "eos 70d"], "resell": 190},               # (est)
        {"words": ["eos m50"], "resell": 210},
        {"words": ["eos m50 ii", "eos m50 mark ii"], "resell": 270},
        {"words": ["eos m100", "eos m10", "eos m200"], "resell": 130},              # (est)
        {"words": ["nikon d3200", "nikon d5100", "nikon d3100"], "resell": 80},     # (est)
        {"words": ["nikon d3300", "nikon d5200", "nikon d5300"], "resell": 110},    # (est)
        {"words": ["nikon d3400", "nikon d5500", "nikon d7000"], "resell": 130},    # (est)
        {"words": ["nikon d3500", "nikon d5600"], "resell": 160},                   # (est)
        # --- action cameras ---
        {"words": ["hero 5", "hero5", "hero 6", "hero6"], "resell": 55},            # (est)
        {"words": ["hero 7", "hero7"], "resell": 70},                               # (est)
        {"words": ["hero 8", "hero8"], "resell": 85},
        {"words": ["hero 9", "hero9"], "resell": 125},
        {"words": ["hero 10", "hero10"], "resell": 150},                            # (est)
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
                     "polo bear", "hi tech", "rrl", "double rl", "purple label"],
    "mertra_tnf": ["heat reactive", "heat-reactive", "colour change", "color change"],
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
#   postage=N        your postage cost for this item
# size_kind None = no size filter (kids are still blocked)
# ---------------------------------------------------------------
def _t(query, resell, channel, kind, max_buy=None, **extra):
    if max_buy is None:
        max_buy = extra.get("alert_under") or max_buy_for(resell, channel, extra.get("postage"))
    d = {"query": query, "resell": resell, "max_buy": max_buy, "channel": channel, "kind": kind}
    d.update(extra)
    return d


def _cam(query, resell, **extra):
    """A camera search: no size filter, minimum buy 8 pounds (anything cheaper is usually junk)."""
    extra.setdefault("min_buy", 8)
    extra.setdefault("items", 15)
    return _t(query, resell, "cameras", None, **extra)


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

    # ===============================================================
    # CAMERAS (Vinted sourcing, no phones).
    # Strategy: search whole FAMILIES (sellers misprice what they cannot identify),
    # then MODEL_TIERS above recognises the exact model inside each title and
    # raises the resell price. Unknown models only alert at very low prices.
    # Prices: UK used listings checked Nov 2026 (MPB, Wex, Vinted asks, forums),
    # scaled DOWN for a private sale. REPLACE WITH YOUR OWN eBay SOLD PRICES.
    # ===============================================================

    # --- digicam families (cheap lane) ---
    _cam("canon ixus", 40, items=30),
    _cam("canon powershot", 40, items=30),
    _cam("sony cybershot", 40, items=30),
    _cam("sony cyber-shot", 40, items=30),
    _cam("nikon coolpix", 35, items=30),
    _cam("fujifilm finepix", 35, items=30),
    _cam("panasonic lumix", 40, items=30),
    _cam("casio exilim", 35, items=30),
    _cam("olympus mju", 70, items=30),
    _cam("y2k digital camera", 40, items=30),
    _cam("ccd digital camera", 45, items=30),
    _cam("digicam", 40, items=30),

    # --- film cameras (the classic underpriced "old camera" listings) ---
    _cam("film camera", 25, items=30),
    _cam("35mm compact camera", 25, items=30),
    _cam("point and shoot film camera", 25, items=30),
    _cam("vintage camera", 25, items=30),

    # --- budget DSLRs, mirrorless, action cams (heavier = postage 8) ---
    _cam("canon eos dslr", 60, postage=8, items=30),
    _cam("nikon dslr", 60, postage=8, items=30),
    _cam("sony alpha camera", 80, postage=7, items=30),
    _cam("gopro hero", 50, items=30),

    # --- specific high-value models people often list too cheaply ---
    _cam("olympus mju ii", 170),
    _cam("contax t2", 600, postage=6),
    _cam("yashica t4", 350),
    _cam("konica big mini", 150),
    _cam("leica mini zoom", 120),
    _cam("olympus xa", 140),
    _cam("ricoh gr iii", 700, postage=6),
    _cam("ricoh gr ii", 450, postage=6),
    _cam("sony rx100", 220, postage=6),
    _cam("canon g7x", 350, postage=6),
    _cam("canon eos m50", 210, postage=7),
    _cam("sony a6000", 230, postage=7),
    _cam("pentax k1000", 100, postage=7),
    _cam("canon ae-1", 90, postage=7),
    _cam("nikon fm2", 250, postage=7),
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
