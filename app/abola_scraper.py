import logging
from urllib.parse import urljoin, urlparse, urlunparse
import xml.etree.ElementTree as ET
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

ABOLA_RSS_URL = "https://www.abola.pt/rss-articles.xml"
BLACKLIST_SUBSTR = ("/video/", "/a-bola-tv/", "/programas/", "/videocasts/")

def _canonical(u: str) -> str:
    """Removes query strings and fragments from a URL."""
    try:
        pu = urlparse(u)
        return urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
    except Exception:
        return u

def _is_valid_abola_article_url(url: str) -> bool:
    """Checks if a URL is a candidate for a valid A Bola news article."""
    if not url.endswith(".html"):
        return False
    if any(s in url for s in BLACKLIST_SUBSTR):
        return False
    return True

class ABolaScraper(BaseScraper):
    """
    Scraper for A Bola news.
    It uses the official RSS feed to discover articles, which is more stable than HTML scraping.
    """

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "abola.pt"

    def extract_article_links(self, html, base_url, section=None):
        """
        Extracts article links from A Bola's official RSS feed.
        The html and base_url parameters are ignored as we fetch the RSS feed directly.
        """
        logger.info(f"Fetching A Bola articles from official RSS feed: {ABOLA_RSS_URL}")
        try:
            response = self.session.get(ABOLA_RSS_URL, timeout=15)
            response.raise_for_status()
            
            # Using standard library's ElementTree to parse XML
            root = ET.fromstring(response.content)
            
            raw_links = [item.findtext('link') for item in root.findall('./channel/item') if item.findtext('link')]

            # Filter and clean the links
            unique_links = set()
            for link in raw_links:
                canonical_link = _canonical(link)
                if _is_valid_abola_article_url(canonical_link):
                    unique_links.add(canonical_link)

            logger.info(f"Found {len(unique_links)} unique and valid links from A Bola RSS feed for section '{section}'.")
            return list(unique_links)

        except Exception as e:
            logger.error(f"Failed to fetch or parse A Bola RSS feed: {e}", exc_info=True)
            return []

    def find_next_page_url(self, html, current_url):
        """Pagination is not needed as we use the full RSS feed."""
        return None