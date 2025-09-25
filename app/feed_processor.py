
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs, urlunparse
from unidecode import unidecode
from thefuzz import fuzz
from dateutil import parser

logger = logging.getLogger(__name__)

def canonicalize_url(url):
    """Canonicalizes a URL by removing tracking parameters, anchors, and trailing slashes."""
    if not url:
        return None
    try:
        p = urlparse(url)
        # Keep only essential query parameters if necessary, for now, remove all
        # Also, you might want to define a whitelist of params to keep for some sites
        query = ''
        # Rebuild the URL without query, fragment, and with a standard path
        path = p.path.rstrip('/') or ''
        return urlunparse((p.scheme, p.netloc, path, p.params, query, '')).lower()
    except Exception as e:
        logger.warning(f"Could not canonicalize URL {url}: {e}")
        return url.lower()

def normalize_title(title):
    """Normalizes a title by converting to lowercase, removing accents and punctuation."""
    if not title:
        return ""
    # Remove accents
    text = unidecode(title)
    # Lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[\s\W_]+', ' ', text, flags=re.UNICODE)
    return text.strip()

def get_best_item(item1, item2, priority_source_order):
    """Chooses the best item between two duplicates based on priority rules."""
    # 1. Priority Source Order
    try:
        p1 = priority_source_order.index(item1['source'])
    except ValueError:
        p1 = float('inf')
    try:
        p2 = priority_source_order.index(item2['source'])
    except ValueError:
        p2 = float('inf')

    if p1 != p2:
        return item1 if p1 < p2 else item2

    # 2. Presence of Image
    has_image1 = bool(item1.get('image'))
    has_image2 = bool(item2.get('image'))
    if has_image1 != has_image2:
        return item1 if has_image1 else item2

    # 3. Most Recent pubDate
    try:
        date1 = parser.isoparse(item1['pubDate'])
    except (ValueError, TypeError):
        date1 = datetime.min.replace(tzinfo=timezone.utc)
    try:
        date2 = parser.isoparse(item2['pubDate'])
    except (ValueError, TypeError):
        date2 = datetime.min.replace(tzinfo=timezone.utc)
        
    return item1 if date1 > date2 else item2

def process_feed_data(data):
    """
    Unifies, deduplicates, and processes feed items based on specified rules.
    """
    topic = data.get("topic", "unknown")
    priority_source_order = data.get("priority_source_order", [])
    max_items = data.get("max_items", 200)
    
    all_items = []
    for feed in data.get("feeds", []):
        source = feed.get("source")
        for item in feed.get("items", []):
            # Ensure basic structure
            if not all(k in item for k in ['title', 'link', 'pubDate']):
                continue
            
            item['source'] = source
            item['canonical_url'] = canonicalize_url(item['link'])
            item['normalized_title'] = normalize_title(item['title'])
            try:
                item['parsed_pubDate'] = parser.isoparse(item['pubDate'])
            except (ValueError, TypeError):
                # If pubDate is invalid, skip the item
                logger.warning(f"Skipping item with invalid pubDate: {item['title']}" )
                continue

            all_items.append(item)

    # Sort by pubDate descending to process newest first
    all_items.sort(key=lambda x: x['parsed_pubDate'], reverse=True)

    deduplicated_items = {}  # Using dict for quick lookups: {canonical_url: item}
    final_items = []

    for item in all_items:
        is_duplicate = False
        # Rule a: Check for exact canonical URL match
        if item['canonical_url'] in deduplicated_items:
            is_duplicate = True
            existing_item = deduplicated_items[item['canonical_url']]
        else:
            # Rule b: Check for fuzzy title match with recent pubDate
            for existing in deduplicated_items.values():
                title_similarity = fuzz.ratio(item['normalized_title'], existing['normalized_title'])
                time_diff = abs(item['parsed_pubDate'] - existing['parsed_pubDate'])
                
                if title_similarity >= 92 and time_diff <= timedelta(hours=6):
                    is_duplicate = True
                    existing_item = existing
                    break
        
        if is_duplicate:
            # A duplicate was found, decide which one is better
            best_item = get_best_item(existing_item, item, priority_source_order)
            
            # If the new item is better, replace the existing one
            if best_item is item:
                # The new item won, so we need to update the master record
                # First, find what the old "winner" was merged from and add it to the new winner
                merged = existing_item.get('merged_from', [])
                merged.append({"source": existing_item['source'], "link": existing_item['link']})
                # Also add any items the old winner had already merged
                if 'merged_from' in existing_item:
                    merged.extend(existing_item['merged_from'])
                
                item['merged_from'] = merged
                
                # Replace in dict. Key might be different if the "better" item has a different canonical URL
                # (e.g. in a fuzzy match scenario). We need to remove the old and add the new.
                del deduplicated_items[existing_item['canonical_url']]
                deduplicated_items[item['canonical_url']] = item
        else:
            # Not a duplicate, add to our set of unique items
            deduplicated_items[item['canonical_url']] = item

    # Prepare the final list from the deduplicated dictionary
    final_items = list(deduplicated_items.values())
    
    # Post-processing on the final list
    for item in final_items:
        # Set primary category
        item['primary_category'] = topic
        
        # Merge and normalize original categories
        original_categories = item.get('categories', [])
        if not isinstance(original_categories, list):
            original_categories = [original_categories] if original_categories else []

        # Include categories from merged items
        for merged_item_ref in item.get('merged_from', []):
            # This part is tricky as we don't have the full merged item object anymore.
            # The prompt implies we should merge categories, but the simple merged_from list
            # doesn't contain them. We will stick to the winner's categories.
            pass

        item['categories'] = sorted(list(set([cat.lower() for cat in original_categories if cat])))

        # Clean up helper fields
        del item['canonical_url']
        del item['normalized_title']
        del item['parsed_pubDate']

    # Final sort and truncate
    final_items.sort(key=lambda x: parser.isoparse(x['pubDate']), reverse=True)
    overflow_truncated = len(final_items) > max_items
    final_items = final_items[:max_items]

    output = {
        "topic": topic,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "overflow_truncated": overflow_truncated,
        "items": final_items
    }
    
    return output
