# app/order_feed_desc.py
from datetime import datetime, timezone
from email.utils import format_datetime
# Import the CORRECT date utility from the project
from .utils import best_dt 

def order_desc(items, channel=None):
    """
    Sorts a list of article items in descending order of date.
    This function does NOT filter or deduplicate, it only sorts.
    It also updates the 'lastBuildDate' in the provided channel dictionary.
    """
    # Sort using the project's own best_dt function for reliable date extraction
    items.sort(key=best_dt, reverse=True)
    
    if channel is not None and items:
        # Get the date from the newest item (now at index 0)
        newest_date = best_dt(items[0])
        
        # Fallback to now() if the best item has no date, though unlikely
        if newest_date == datetime.min.replace(tzinfo=timezone.utc):
             newest_date = datetime.now(timezone.utc)

        # Format the date correctly for the RSS channel
        channel["lastBuildDate"] = format_datetime(newest_date)
        
    return items