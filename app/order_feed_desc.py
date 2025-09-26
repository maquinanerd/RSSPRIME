# order_feed_desc.py
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, format_datetime

def _to_dt(it):
    # tenta várias chaves comuns de data; cai p/ 1970 se não achar
    for k in ("pubDate", "published", "updated", "dc:date", "date", "isoDate"):
        v = it.get(k)
        if not v:
            continue
        # RFC 2822 (ex: "Thu, 25 Sep 2025 23:13:38 -0300")
        try:
            return parsedate_to_datetime(v).astimezone(timezone.utc)
        except Exception:
            pass
        # ISO 8601 (ex: "2025-09-25T23:13:38-03:00" ou "2025-09-25T23:13:38Z")
        try:
            v2 = v.replace("Z", "+00:00")
            return datetime.fromisoformat(v2).astimezone(timezone.utc)
        except Exception:
            pass
    return datetime(1970, 1, 1, tzinfo=timezone.utc)

def order_desc(items, channel=None):
    # mantém TODOS os itens; só reordena por data desc
    items.sort(key=_to_dt, reverse=True)
    if channel is not None and items:
        channel["lastBuildDate"] = format_datetime(_to_dt(items[0]))
    return items
