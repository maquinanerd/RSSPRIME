import logging
import feedparser
from urllib.parse import urljoin, urlparse, urlunparse
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

ABOLA_RSS = "https://www.abola.pt/rss-articles.xml"
BLACKLIST_SUBSTR = ("/video/", "/a-bola-tv/", "/programas/", "/videocasts/")

def _canonical(u: str) -> str:
    try:
        pu = urlparse(u)
        return urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
    except Exception:
        return u

def _is_valid_abola_article_url(url: str) -> bool:
    """Checks if a URL is a candidate for a valid A Bola news article."""
    if not url:
        return False

    path = urlparse(url).path.lower()
    # Article URLs typically contain /noticia/
    if '/noticia/' not in path:
        return False

    if any(s in url for s in BLACKLIST_SUBSTR):
        return False
    return True

class ABolaScraper(BaseScraper):
    source = "abola"

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "abola.pt"

    def extract_article_links(self, html, base_url, section=None):
        """
        Extracts article links from A Bola's official RSS feed.
        The html and base_url parameters are ignored as we fetch the RSS feed directly.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UnifiedFeedBot/1.0",
            "Accept": "application/rss+xml, application/atom+xml, */*",
            "Accept-Language": "pt-PT,pt-BR;q=0.9,en;q=0.8",
        }
        try:
            r = self.session.get(ABOLA_RSS, headers=headers, timeout=15)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)

            if parsed.bozo:
                logger.warning(f"Feedparser reported an error parsing A Bola RSS feed: {parsed.bozo_exception}")

            links = []
            for e in parsed.entries:
                link = e.get("link") or e.get("id")
                if not link:
                    continue
                
                canonical_link = _canonical(link)
                if _is_valid_abola_article_url(canonical_link):
                    links.append(canonical_link)

            out, seen = [], set()
            for u in links:
                if u not in seen:
                    seen.add(u)
                    out.append(u)

            logger.info(f"[abola/{section}] Found {len(out)} links from RSS")
            if not out:
                logger.warning(f"[abola/{section}] No article links found via RSS")
            return out

        except Exception as e:
            logger.error(f"Failed to fetch or parse A Bola RSS feed: {e}", exc_info=True)
            return []

    def find_next_page_url(self, html, current_url):
        """Pagination is not needed as we use the full RSS feed."""
        return None