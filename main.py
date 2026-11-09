import os
import json
import requests

# Safely try loading local .env file (for local testing), skip on GitHub Actions
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SEEN_FILE = "seen_items.json"

# Webhook mapping (read from environment variables / GitHub Secrets)
WEBHOOK_MAP = {
    "Stussy": os.environ.get("WEBHOOK_STUSSY_SUPREME"),
    "Supreme": os.environ.get("WEBHOOK_STUSSY_SUPREME"),
    "Carhartt": os.environ.get("WEBHOOK_CARHARTT"),
    "Ralph Lauren": os.environ.get("WEBHOOK_RALPH_LAUREN"),
    "Nike": os.environ.get("WEBHOOK_NIKE_ADIDAS"),
    "Adidas": os.environ.get("WEBHOOK_NIKE_ADIDAS")
}

DEFAULT_WEBHOOK = os.environ.get("WEBHOOK_CARHARTT")

# 🚫 BLACKLIST / NEGATIVE FILTERS
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
    
    # Select specific brand webhook, or fallback to default
    webhook_url = WEBHOOK_MAP.get(brand) or DEFAULT_WEBHOOK
    
    if not webhook_url:
        print(f"⚠️ Warning: No webhook configured for brand '{brand}'. Check your GitHub Secrets!")
        return

    embed = {
        "title": f"🚨 {item.get('title', 'Steal Alert!')}",
        "url": item.get("url", "#"),
        "color": 3066993,  # Green accent
        "fields": [
            {"name": "Price", "value": f'£{item.get("price")}', "inline": True},
            {"name": "Size", "value": str(item.get("size")), "inline": True},
            {"name": "Brand", "value": brand, "inline": True},
            {"name": "Est. Net Profit", "value": f'£{item.get("profit", 10)}+', "inline": True}
        ],
        "footer": {"text": "DealHunt HQ • Automated Alert"}
    }

    try:
        response = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        if response.status_code in [200, 204]:
            print(f"✅ Alert sent successfully for '{item.get('title')}'!")
        else:
            print(f"❌ Failed to send alert ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Webhook request error: {e}")


def fetch_vinted_deals():
    """
    Initializes a session to obtain Vinted cookies and fetches live catalog listings.
    """
    all_found_items = []
    
    search_queries = [
        "Carhartt Detroit Jacket",
        "Stussy hoodie",
        "Supreme tee",
        "Ralph Lauren half zip",
        "Nike vintage sweater",
        "Adidas vintage jacket"
    ]
    
    # Use a persistent session to retain session cookies
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en;q=0.9"
    })

    # Step 1: Hit Vinted homepage to obtain session cookies
    try:
        init_res = session.get("https://www.vinted.co.uk", timeout=10)
        print(f"🌐 Vinted session initialization status: {init_res.status_code}")
    except Exception as e:
        print(f"⚠️ Session init failed: {e}")

    # Step 2: Query the API endpoints
    for query in search_queries:
        try:
            url = f"https://www.vinted.co.uk/api/v2/catalog/items?search_text={query}&order=newest_first"
            response = session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                print(f"🔎 Query '{query}': fetched {len(items)} items.")
                
                for item in items:
                    item_id = str(item.get("id"))
                    title = item.get("title", "")
                    price = float(item.get("price", 0))
                    
                    # Extract brand title
                    brand_info = item.get("brand_title") or item.get("brand", {})
                    brand = brand_info if isinstance(brand_info, str) else brand_info.get("title", "Unknown")
                    
                    size = str(item.get("size_title", ""))
                    item_url = item.get("url", "")
                    description = item.get("description", "")
                    
                    all_found_items.append({
                        "id": item_id,
                        "title": title,
                        "brand": brand,
                        "size": size,
                        "price": price,
                        "profit": 12.0,  # Baseline profit for testing
                        "url": item_url,
                        "description": description
                    })
            else:
                print(f"⚠️ Vinted API returned HTTP {response.status_code} for query '{query}'")
                
        except Exception as e:
            print(f"❌ Error fetching query '{query}': {e}")

    print(f"📊 Total items retrieved across queries: {len(all_found_items)}")
    return all_found_items


def main():
    seen_items = load_seen_items()
    print(f"🧠 Memory loaded: {len(seen_items)} previously seen item IDs.")
    
    new_items_found = fetch_vinted_deals()
    alerts_sent = 0
    
    for item in new_items_found:
        item_id = str(item.get("id"))
        
        # 1. DUPLICATE CHECK
        if item_id in seen_items:
            continue

        # 2. SIZE & PROFIT CHECKS (Flexible size matching)
        raw_size = str(item.get("size", "")).upper()
        profit = item.get("profit", 0)
        
        # Check if any target size (M, L, XL) appears in the size string
        has_valid_size = any(s in raw_size for s in ["M", "L", "XL"])
        
        if not has_valid_size or profit < 10:
            continue

        # 3. NEGATIVE KEYWORD FILTERS
        if not passes_negative_filters(item):
            continue

        # Trigger Discord Alert
        send_discord_alert(item)
        seen_items.add(item_id)
        alerts_sent += 1

    print(f"🏁 Run complete: Sent {alerts_sent} new alerts.")
    save_seen_items(seen_items)


if __name__ == "__main__":
    main()
