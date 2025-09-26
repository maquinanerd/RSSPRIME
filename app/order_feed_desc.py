# app/order_feed_desc.py
from datetime import datetime, timezone
from email.utils import format_datetime
from .utils import best_dt 

def order_desc(items, channel=None):
    """
    Sorts a list of article items in descending order of date.
    This function does NOT filter or deduplicate, it only sorts.
    It also updates the 'lastBuildDate' in the provided channel dictionary.
    """
    # Create a new sorted list instead of sorting in-place
    sorted_items = sorted(items, key=best_dt, reverse=True)
    
    if channel is not None and sorted_items:
        # Get the date from the newest item (now at index 0)
        newest_date = best_dt(sorted_items[0])
        
        # Fallback to now() if the best item has no date, though unlikely
        if newest_date == datetime.min.replace(tzinfo=timezone.utc):
             newest_date = datetime.now(timezone.utc)

        # Format the date correctly for the RSS channel
        channel["lastBuildDate"] = format_datetime(newest_date)
        
    return sorted_items
