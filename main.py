import time
import requests
from vinted_scraper import VintedScraper

# 🎯 Your active Discord Webhook URL
DISCORD_WEBHOOK_URL = (
    "https://discordapp.com/api/webhooks/1569080189470638310/XXsJJJ_hcLXMtb-z71kgwKb62TTGWXFRE21GoSZkvqpZatMGy9P9aIjCUhmS52eY3fJ6"
)

# 💰 Baseline Rules: Min £6 buy cost, strictly £10+ net profit minimum
MIN_BUY_PRICE = 6.0
MIN_NET_PROFIT = 10.0

# 🎯 Ruthless Streetwear Search Targets & Conservative Resell Benchmarks
TARGET_SEARCHES = [
    # Carhartt Heavy Hitters
    {"query": "carhartt jacket", "target_resell": 45.0, "max_buy": 25.0},
    {"query": "carhartt hoodie", "target_resell": 32.0, "max_buy": 18.0},
    {"query": "carhartt Detroit", "target_resell": 65.0, "max_buy": 40.0},

    # Ralph Lauren Pickups
    {"query": "ralph lauren fleece", "target_resell": 30.0, "max_buy": 15.0},
    {"query": "ralph lauren jacket", "target_resell": 38.0, "max_buy": 20.0},
    {"query": "ralph lauren bear hoodie", "target_resell": 35.0, "max_buy": 18.0},

    # Streetwear & Grail Brands
    {"query": "stussy hoodie", "target_resell": 40.0, "max_buy": 22.0},
    {"query": "stussy t-shirt", "target_resell": 24.0, "max_buy": 10.0},
    {"query": "supreme hoodie", "target_resell": 55.0, "max_buy": 32.0},
    {"query": "supreme t-shirt", "target_resell": 28.0, "max_buy": 14.0},
    {"query": "palace hoodie", "target_resell": 48.0, "max_buy": 26.0},
    {"query": "palace t-shirt", "target_resell": 25.0, "max_buy": 12.0},
    {"query": "bape ape head tee", "target_resell": 32.0, "max_buy": 16.0},
    {"query": "broken planet hoodie", "target_resell": 45.0, "max_buy": 25.0},
    {"query": "broken planet t-shirt", "target_resell": 25.0, "max_buy": 12.0},
]

# 🛡️ Strict Rep, Jeans & Bad Condition Blacklist
BANNED_TITLE_KEYWORDS = [
    "rep",
    "reps",
    "replica",
    "fake",
    "unbranded",
    "pandabuy",
    "taobao",
    "dhgate",
    "style like",
    "inspired",
    "jeans",
    "pants",
    "trousers",
    "denim",
    "satisfactory",
    "fair condition",
    "heavy wear",
    "damaged",
    "flawed",
]

seen_item_ids = set()
scraper = VintedScraper("https://www.vinted.co.uk")


def is_valid_size(text):
    """Ensures the listing matches adult sizes M, L, or XL."""
    text_lower = text.lower()

    # Keywords that indicate correct adult sizes
    valid_markers = ["medium", "large", "extra large", " sz m", " sz l", " sz xl", "size m", "size l", "size xl"]

    # Also check standalone letters surrounded by spaces or brackets
    exact_tokens = [" m ", " l ", " xl ", "(m)", "(l)", "(xl)", "[m]", "[l]", "[xl]"]

    for marker in valid_markers:
        if marker in text_lower:
            return True

    for token in exact_tokens:
        if token in text_lower:
            return True

    # Check if title ends with size
    if text_lower.endswith(" m") or text_lower.endswith(" l") or text_lower.endswith(" xl"):
        return True

    return False


def is_suspicious_title(title):
    title_lower = title.lower()
    for keyword in BANNED_TITLE_KEYWORDS:
        if keyword in title_lower:
            return True
    return False


def send_discord_alert(title, price, item_url, target_resell, net_profit):
    """Sends a clean alert card straight to your Discord."""
    price_val = float(price)

    payload = {
        "username": "Streetwear Grail Hunter 🎯",
        "embeds": [
            {
                "title": f"🔥 M/L/XL STREETWEAR STEAL: {title}",
                "url": item_url,
                "color": 15158332,
                "fields": [
                    {
                        "name": "Buy Price",
                        "value": f"**£{price_val:.2f}**",
                        "inline": True,
                    },
                    {
                        "name": "Est. Resell",
                        "value": f"**£{target_resell:.2f}**",
                        "inline": True,
                    },
                    {
                        "name": "Est. Net Profit",
                        "value": f"**+£{net_profit:.2f}** 💰",
                        "inline": True,
                    },
                    {
                        "name": "🔍 Quick Authenticity Checklist",
                        "value": "• Check inner care tag stitching & neck tag density\n• Check logo alignment & embroidery quality\n• Review seller rating & feedback history",
                        "inline": False,
                    },
                ],
                "footer": {"text": "Tap title to inspect & buy on Vinted!"},
            }
        ],
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code == 204:
        print(f"✅ M/L/XL Alert Sent: {title} (£{price_val:.2f}) -> Profit: +£{net_profit:.2f}")
    else:
        print(f"❌ Failed to send Discord alert: {response.status_code}")


def check_vinted_deals():
    for target in TARGET_SEARCHES:
        query_text = target["query"]
        target_resell = target["target_resell"]
        max_buy = target["max_buy"]

        print(f"🔎 Scanning Vinted for '{query_text}' (M, L, XL only)...")

        try:
            search_params = {
                "search_text": query_text,
                "order": "newest_first",
            }

            items = scraper.search(search_params)

            for item in items[:6]:
                item_id = str(
                    getattr(item, "id", None)
                    or (item.get("id") if isinstance(item, dict) else None)
                )

                if item_id and item_id in seen_item_ids:
                    continue

                if isinstance(item, dict):
                    raw_price = item.get("price")
                    item_title = item.get("title", "Unknown Item")
                    item_desc = item.get("description", "") or ""
                    raw_url = item.get("url", "https://www.vinted.co.uk")
                else:
                    raw_price = getattr(item, "price", None)
                    item_title = getattr(item, "title", "Unknown Item")
                    item_desc = getattr(item, "description", "") or ""
                    raw_url = getattr(item, "url", "https://www.vinted.co.uk")

                if raw_price is None:
                    continue

                # Combine title and description to check sizes and condition flags thoroughly
                full_listing_text = f"{item_title} {item_desc}"

                # Size enforcement: Must be M, L, or XL
                if not is_valid_size(full_listing_text):
                    if item_id:
                        seen_item_ids.add(item_id)
                    continue

                try:
                    if isinstance(raw_price, str):
                        clean_str = "".join(
                            c for c in raw_price if c.isdigit() or c == "."
                        )
                        item_price = float(clean_str)
                    else:
                        item_price = float(raw_price)
                except (ValueError, TypeError):
                    continue

                # Strict Profit Guard: Target profit must be £10+ minimum
                net_profit = target_resell - item_price

                if MIN_BUY_PRICE <= item_price <= max_buy and net_profit >= MIN_NET_PROFIT:
                    if not raw_url or raw_url == "0":
                        item_url = "https://www.vinted.co.uk"
                    elif isinstance(raw_url, str):
                        if raw_url.startswith("/"):
                            item_url = f"https://www.vinted.co.uk{raw_url}"
                        elif not raw_url.startswith("http"):
                            item_url = (
                                f"https://www.vinted.co.uk/{raw_url.lstrip('/')}"
                            )
                        else:
                            item_url = raw_url
                    else:
                        item_url = "https://www.vinted.co.uk"

                    # Check for bad condition words or reps
                    if is_suspicious_title(full_listing_text):
                        if item_id:
                            seen_item_ids.add(item_id)
                        continue

                    send_discord_alert(
                        title=item_title,
                        price=item_price,
                        item_url=item_url,
                        target_resell=target_resell,
                        net_profit=net_profit,
                    )

                    if item_id:
                        seen_item_ids.add(item_id)

            time.sleep(3)

        except Exception as e:
            print(f"⚠️ Search loop notice for '{query_text}': {e}")


if __name__ == "__main__":
    print("🚀 Running cloud sweep for Vinted deals...")
    check_vinted_deals()
    print("✅ Sweep complete! Closing cloud runner until next scheduled run.")
