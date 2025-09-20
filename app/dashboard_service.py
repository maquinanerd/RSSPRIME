import logging
from datetime import datetime

from .store import ArticleStore
from .sources_config import SOURCES_CONFIG

logger = logging.getLogger(__name__)


async def safe_get_stats():
    """Safely fetches statistics from the data store."""
    try:
        store = ArticleStore()
        stats = store.get_stats()
        total_articles = stats.get('total_articles', 0)
        last_update_str = stats.get('last_update')

        if last_update_str:
            # Parse and format the date string, removing microseconds for cleaner display
            last_update = datetime.fromisoformat(last_update_str).strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_update = "Nunca"

        return {
            "total_articles": total_articles,
            "last_update": last_update,
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}")
        return {
            "total_articles": 0,
            "last_update": "Erro",
        }


async def safe_get_sources_structure():
    """
    Builds a structured list of sources and their sections for the dashboard,
    making it easy for the template to render them dynamically.
    """
    try:
        # This structure groups feeds for better presentation on the dashboard.
        structured_sources = [
            {
                "group_title": "🇧🇷 Feeds Nacionais",
                "feeds": [
                    {"source_key": "lance", "icon": "🔥", "border": "primary", "header": "primary"},
                    {"source_key": "ge", "icon": "🌟", "border": "success", "header": "success"},
                    {"source_key": "g1", "icon": "📰", "border": "info", "header": "info"},
                    {"source_key": "folha", "icon": "📰", "border": "secondary", "header": "secondary"},
                ]
            },
            {
                "group_title": "🌎 Feeds Internacionais - América Latina",
                "feeds": [
                    {"source_key": "ole", "icon": "🇦🇷", "border": "info", "header": "info"},
                    {"source_key": "as_cl", "icon": "🇨🇱", "border": "danger", "header": "danger"},
                    {"source_key": "as_co", "icon": "🇨🇴", "border": "warning", "header": "warning"},
                    {"source_key": "as_mx", "icon": "🇲🇽", "border": "success", "header": "success"},
                ]
            },
            {
                "group_title": "🇪🇺 Feeds Internacionais - Europa",
                "feeds": [
                    {"source_key": "as_es", "icon": "🇪🇸", "border": "danger", "header": "danger"},
                    {"source_key": "marca", "icon": "🇪🇸", "border": "danger", "header": "danger"},
                    {"source_key": "theguardian", "icon": "🇬🇧", "border": "dark", "header": "dark"},
                    {"source_key": "lequipe", "icon": "🇫🇷", "border": "primary", "header": "primary"},
                    {"source_key": "kicker", "icon": "🇩🇪", "border": "dark", "header": "dark"},
                    {"source_key": "gazzetta", "icon": "🇮🇹", "border": "success", "header": "success"},
                    {"source_key": "abola", "icon": "🇵🇹", "border": "danger", "header": "danger"},
                ]
            },
            {
                "group_title": "🇺🇸 Feeds Internacionais - EUA",
                "feeds": [
                    {"source_key": "foxsports", "icon": "🇺🇸", "border": "primary", "header": "primary"},
                    {"source_key": "cbssports", "icon": "🇺🇸", "border": "info", "header": "info"},
                ]
            }
        ]

        # Populate with actual data from SOURCES_CONFIG
        for group in structured_sources:
            # Filter out feeds that are not in SOURCES_CONFIG
            group["feeds"] = [feed for feed in group["feeds"] if feed["source_key"] in SOURCES_CONFIG]

            for feed_meta in group["feeds"]:
                source_config = SOURCES_CONFIG.get(feed_meta["source_key"])
                if source_config:
                    feed_meta["source_name"] = source_config.get("name")
                    feed_meta["sections"] = source_config.get("sections")

        # Filter out empty groups
        structured_sources = [group for group in structured_sources if group["feeds"]]

        return structured_sources
    except Exception as e:
        logger.error(f"Failed to build sources structure: {e}")
        return []


def build_examples(request):
    """Builds example URLs based on the current request's root URL."""
    base_url = request.url_root
    return {
        "uol_economia_limit": f"{base_url}feeds/uol/economia/rss?limit=20",
        "folha_atom_lula": f"{base_url}feeds/folha/politica/atom?q=Lula",
        "lance_flamengo": f"{base_url}feeds/lance/futebol/rss?q=flamengo",
        "uol_refresh": f"{base_url}feeds/uol/mundo/rss?refresh=1",
    }


async def get_dashboard_data_safe(request):
    """
    Safely fetches all data required for the dashboard, aggregating from other
    safe functions to prevent template rendering errors.
    """
    try:
        stats = await safe_get_stats()
        sources = await safe_get_sources_structure()
        examples = build_examples(request)

        return {
            "stats": stats,
            "sources": sources,
            "examples": examples,
            "request": request,
        }
    except Exception:
        logger.exception("Critical failure while building dashboard data")
        return {"stats": {}, "sources": [], "examples": {}, "request": request}