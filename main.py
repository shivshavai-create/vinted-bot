import os
import json
import requests

# Tries to load local .env file (for your laptop), 
# but safely skips if it's running on GitHub Actions!
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SEEN_FILE = "seen_items.json"

# Map brands to their environment variable names
WEBHOOK_MAP = {
    "Stussy": os.environ.get("WEBHOOK_STUSSY_SUPREME"),
    "Supreme": os.environ.get("WEBHOOK_STUSSY_SUPREME"),
    "Carhartt": os.environ.get("WEBHOOK_CARHARTT"),
    "Ralph Lauren": os.environ.get("WEBHOOK_RALPH_LAUREN"),
    "Nike": os.environ.get("WEBHOOK_NIKE_ADIDAS"),
    "Adidas": os.environ.get("WEBHOOK_NIKE_ADIDAS")
}

# General fallback webhook
DEFAULT_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_CARHARTT")

# 🚫 BLACKLIST / NEGATIVE FILTERS:
# If any of these words appear in the title or description, the bot instantly drops it!
EXCLUDED_KEYWORDS = [
    "realtree", 
    "style", 
    "inspired", 
    "replica", 
    "fake", 
    "custom", 
    "print", 
    "copy", 
    "bootleg"
]


def load_seen_items():
    """Loads the set of previously alert-sent item IDs from file."""
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            return set()
    return set()


def save_seen_items(seen_items):
    """Saves the last 1,000 item IDs to keep the file small."""
    recent_items = list(seen_items)[-1000:]
    with open(SEEN_FILE, "w") as f:
        json.dump(recent_items, f, indent=2)


def passes_negative_filters(item):
    """Checks if the item contains any blacklisted scam or unwanted keywords."""
    title = item.get("title", "").lower()
    description = item.get("description", "").lower()
    full_text = f"{title} {description}"

    for bad_word in EXCLUDED_KEYWORDS:
        if bad_word in full_text:
            print(f"🚫 Filtered out junk containing '{bad_word}': {item.get('title')}")
            return False
    return True


def send_discord_alert(item):
    """Routes the item alert to the specific Discord webhook channel."""
    brand = item.get("brand", "").strip()
    
    webhook_url = WEBHOOK_MAP.get(brand, DEFAULT_WEBHOOK)
    
    if not webhook_url:
        print(f"⚠️ Warning: No webhook configured for brand '{brand}'. Skipping alert.")
        return

    embed = {
        "title": f"🚨 {item.get('title', 'Steal Alert!')}",
        "url": item.get("url", "#"),
        "color": 3066993,  # Green accent color
        "fields": [
            {"name": "Price", "value": f"£{item.get('price')}", "inline": True},
            {"name": "Size", "value": str(item.get("size")), "inline": True},
            {"name": "Brand", "value": brand, "inline": True},
            {"name": "Est. Net Profit", "value": f"£{item.get('profit', 10)}+", "inline": True}
        ],
        "footer": {"text": "DealHunt HQ • Clean Filtered Alert"}
    }

    response = requests.post(webhook_url, json={"embeds": [embed]})
    if response.status_code in [200, 204]:
        print(f"✅ Clean alert sent for '{item.get('title')}'!")
    else:
        print(f"❌ Failed to send alert: {response.status_code}")


def fetch_vinted_deals():
    """
    Placeholder for your Vinted scraping logic.
    Returns a list of items found during this scan.
    """
    # Replace this mock list with your real scraping function logic!
    return []


def main():
    seen_items = load_seen_items()
    new_items_found = fetch_vinted_deals()
    
    for item in new_items_found:
        item_id = str(item.get("id"))
        
        # 1. DUPLICATE CHECK: Skip if already alerted
        if item_id in seen_items:
            continue

        # 2. SIZE & PROFIT CHECKS
        size = str(item.get("size", "")).upper()
        profit = item.get("profit", 0)
        
        if size not in ["M", "L", "XL"] or profit < 10:
            continue

        # 3. NEGATIVE KEYWORD FILTERS (Blocks 'Realtree', 'Style', 'Replica', etc.)
        if not passes_negative_filters(item):
            continue

        # If it passes all checks, send the alert and save to memory!
        send_discord_alert(item)
        seen_items.add(item_id)

    # Save updated list of IDs back to JSON memory
    save_seen_items(seen_items)


if __name__ == "__main__":
    main()
