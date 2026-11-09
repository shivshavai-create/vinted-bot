import time
import requests
from vinted_scraper import VintedScraper

# 🎯 Dedicated Webhooks per Brand Channel
WEBHOOKS = {
    "carhartt": "https://discordapp.com/api/webhooks/1569080189470638310/XXsJJJ_hcLXMtb-z71kgwKb62TTGWXFRE21GoSZkvqpZatMGy9P9aIjCUhmS52eY3fJ6", # Default channel
    "ralph_lauren": "https://discordapp.com/api/webhooks/1569080189470638310/XXsJJJ_hcLXMtb-z71kgwKb62TTGWXFRE21GoSZkvqpZatMGy9P9aIjCUhmS52eY3fJ6",
    "supreme_palace": "https://discordapp.com/api/webhooks/1569080189470638310/XXsJJJ_hcLXMtb-z71kgwKb62TTGWXFRE21GoSZkvqpZatMGy9P9aIjCUhmS52eY3fJ6",
    "stussy_bape": "https://discordapp.com/api/webhooks/1569080189470638310/XXsJJJ_hcLXMtb-z71kgwKb62TTGWXFRE21GoSZkvqpZatMGy9P9aIjCUhmS52eY3fJ6",
}

# 💰 Baseline Rules
MIN_BUY_PRICE = 6.0
MIN_NET_PROFIT = 10.0

# 🎯 Target Searches mapped to specific Discord channels
TARGET_SEARCHES = [
    # Carhartt Channel
    {"query": "carhartt jacket", "target_resell": 45.0, "max_buy": 25.0, "channel": "carhartt"},
    {"query": "carhartt hoodie", "target_resell": 32.0, "max_buy": 18.0, "channel": "carhartt"},
    {"query": "carhartt Detroit", "target_resell": 65.0, "max_buy": 40.0, "channel": "carhartt"},
    
    # Ralph Lauren Channel
    {"query": "ralph lauren fleece", "target_resell": 30.0, "max_buy": 15.0, "channel": "ralph_lauren"},
    {"query": "ralph lauren jacket", "target_resell": 38.0, "max_buy": 20.0, "channel": "ralph_lauren"},
    {"query": "ralph lauren bear hoodie", "target_resell": 35.0, "max_buy": 18.0, "channel": "ralph_lauren"},
    
    # Supreme & Palace Channel
    {"query": "supreme hoodie", "target_resell": 55.0, "max_buy": 32.0, "channel": "supreme_palace"},
    {"query": "supreme t-shirt", "target_resell": 28.0, "max_buy": 14.0, "channel": "supreme_palace"},
    {"query": "palace hoodie", "target_resell": 48.0, "max_buy": 26.0, "channel": "supreme_palace"},
    {"query": "palace t-shirt", "target_resell": 25.0, "max_buy": 12.0, "channel": "supreme_palace"},

    # Stüssy, Bape & Broken Planet Channel
    {"query": "stussy hoodie", "target_resell": 40.0, "max_buy": 22.0, "channel": "stussy_bape"},
    {"query": "stussy t-shirt", "target_resell": 24.0, "max_buy": 10.0, "channel": "stussy_bape"},
    {"query": "bape ape head tee", "target_resell": 32.0, "max_buy": 16.0, "channel": "stussy_bape"},
    {"query": "broken planet hoodie", "target_resell": 45.0, "max_buy": 25.0, "channel": "stussy_bape"},
    {"query": "broken planet t-shirt", "target_resell": 25.0, "max_buy": 12.0, "channel": "stussy_bape"},
]

# 🛡️ Universal Rep, Junk, Realtree & "Style" Blacklist (Applies to ALL brands)
BANNED_KEYWORDS = [
    "realtree", "camo tree", 
    "style", "styled", "inspired", "type", 
    "rep", "reps", "replica", "fake", "unbranded", "pandabuy", "taobao", "dhgate",
    "jeans", "pants", "trousers", "denim", "shorts",
    "satisfactory", "fair condition", "heavy wear", "damaged", "flawed", "spare or repair"
]

seen_item_ids = set()
scraper = VintedScraper("https://www.vinted.co.uk")


def is_valid_size(text):
    text_lower = text.lower()
    valid_markers = ["medium", "large", "extra large", " sz m", " sz l", " sz xl", "size m", "size l", "size xl"]
    exact_tokens = [" m ", " l ", " xl ", "(m)", "(l)", "(xl)", "[m]", "[l]", "[xl]"]

    for marker in valid_markers:
        if marker in text_lower:
            return True
    for token in exact_tokens:
        if token in text_lower:
            return True
    if text_lower.endswith(" m") or text_lower.endswith(" l") or text_lower.endswith(" xl"):
        return True

    return False


def is_suspicious_listing(full_text):
    """Scans the combined title and description for any blacklisted spam words."""
    text_lower = full_text.lower()
    for keyword in BANNED_KEYWORDS:
        if keyword in text_lower:
            return True
    return False


def send_discord_alert(title, price, item_url, target_resell, net_profit, channel_key):
    """Sends alert to the specific Discord webhook channel."""
    price_val = float(price)
    target_webhook = WEBHOOKS.get(channel_key, WEBHOOKS["carhartt"])

    payload = {
        "username": f"{channel_key.replace('_', ' ').title()} Hunter 🎯",
        "embeds": [
            {
                "title": f"🔥 M/L/XL STEAL: {title}",
                "url": item_url,
                "color": 15158332,
                "fields": [
                    {"name": "Buy Price", "value": f"**£{price_val:.2f}**", "inline": True},
                    {"name": "Est. Resell", "value": f"**£{target_resell:.2f}**", "inline": True},
                    {"name": "Est. Net Profit", "value": f"**+£{net_profit:.2f}** 💰", "inline": True},
                    {
                        "name": "🔍 Quick Authenticity Checklist",
                        "value": "• Check care tag stitching & neck tag density\n• Check logo alignment & embroidery\n• Review seller rating",
                        "inline": False,
                    },
                ],
                "footer": {"text": "Tap title to inspect & buy on Vinted!"},
            }
        ],
    }

    response = requests.post(target_webhook, json=payload)
    if response.status_code == 204:
        print(f"✅ Alert sent to #{channel_key}: {title} (£{price_val:.2f}) -> Profit: +£{net_profit:.2f}")
    else:
        print(f"❌ Failed to send alert to #{channel_key}: {response.status_code}")


def check_vinted_deals():
    for target in TARGET_SEARCHES:
        query_text = target["query"]
        target_resell = target["target_resell"]
        max_buy = target["max_buy"]
        channel_key = target["channel"]

        print(f"\n🔎 Scanning Vinted for '{query_text}'...")

        try:
            search_params = {
                "search_text": query_text,
                "order": "newest_first",
            }

            items = scraper.search(search_params)
            print(f"📦 Vinted returned {len(items) if items else 0} raw items for '{query_text}'")

            if not items:
                continue

            for item in items[:6]:
                item_id = str(
                    getattr(item, "id", None)
                    or (item.get("id") if isinstance(item, dict) else None)
                )

                if item_id and item_id in seen_item_ids:
                    print(f"⏩ Skipping already seen item ID: {item_id}")
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
                    print(f"⚠️ Skipped '{item_title}': No price found.")
                    continue

                full_listing_text = f"{item_title} {item_desc}"

                # 1. Check Size Filter
                if not is_valid_size(full_listing_text):
                    print(f"📏 Skipped (Size mismatch): '{item_title}'")
                    if item_id:
                        seen_item_ids.add(item_id)
                    continue

                # 2. Check Universal Blacklist (Blocks "realtree", "style", "inspired", pants/jeans, etc.)
                if is_suspicious_listing(full_listing_text):
                    print(f"🚫 Skipped (Blacklist/Junk): '{item_title}'")
                    if item_id:
                        seen_item_ids.add(item_id)
                    continue

                try:
                    if isinstance(raw_price, str):
                        clean_str = "".join(c for c in raw_price if c.isdigit() or c == ".")
                        item_price = float(clean_str)
                    else:
                        item_price = float(raw_price)
                except (ValueError, TypeError):
                    print(f"⚠️ Skipped '{item_title}': Invalid price format '{raw_price}'")
                    continue

                net_profit = target_resell - item_price

                print(f"🧮 Checking price £{item_price:.2f} (Max allowed: £{max_buy}) | Profit: £{net_profit:.2f} (Min required: £{MIN_NET_PROFIT})")

                # 3. Check Price and Profit Thresholds
                if MIN_BUY_PRICE <= item_price <= max_buy and net_profit >= MIN_NET_PROFIT:
                    if not raw_url or raw_url == "0":
                        item_url = "https://www.vinted.co.uk"
                    elif isinstance(raw_url, str):
                        if raw_url.startswith("/"):
                            item_url = f"https://www.vinted.co.uk{raw_url}"
                        elif not raw_url.startswith("http"):
                            item_url = f"https://www.vinted.co.uk/{raw_url.lstrip('/')}"
                        else:
                            item_url = raw_url
                    else:
                        item_url = "https://www.vinted.co.uk"

                    send_discord_alert(
                        title=item_title,
                        price=item_price,
                        item_url=item_url,
                        target_resell=target_resell,
                        net_profit=net_profit,
                        channel_key=channel_key,
                    )

                    if item_id:
                        seen_item_ids.add(item_id)
                else:
                    print(f"❌ Failed price/profit bounds for: '{item_title}'")

            time.sleep(3)

        except Exception as e:
            print(f"⚠️ Search loop notice for '{query_text}': {e}")


if __name__ == "__main__":
    print("🚀 Multi-Channel Vinted Hunter Active! Checking every 90 seconds...")
    while True:
        check_vinted_deals()
        print("☕ Sweep complete. Pausing 90s for fresh uploads...")
        time.sleep(90)
