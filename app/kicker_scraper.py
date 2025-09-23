import logging
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Regex to match valid article URLs, e.g., /slug-123456/artikel
ARTICLE_RE = re.compile(r"^/[^?#]+-\d{6,}/artikel(?:[?#].*)?$")
DENY_PATTERNS = [
    "/spieltag", "/tabelle", "/tabellenrechner", "/videos",
    "/live", "/podcast", "/podcastpopup", "/ticker", "/statistik"
]

class KickerScraper(BaseScraper):
    """
    Scraper for Kicker news.
    """

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "kicker.de"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Kicker listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()
 
        # Broad selector for content modules as suggested
        all_anchors = soup.select("section.kick__modul a[href]")
        logger.info(f"[kicker/{section}] links from HTML: found={len(all_anchors)}")

        for a in all_anchors:
            href = a.get("href", "").strip()
            
            # Normalize relative URLs
            full_url = urljoin(base_url, href)
            
            # Use the path for regex matching and filtering
            path = urlparse(full_url).path

            # Filter out non-article links like navigation, videos, etc.
            if any(p in path for p in DENY_PATTERNS):
                continue

            # Keep only pages that match the article pattern (e.g., /slug-123456/artikel)
            if ARTICLE_RE.search(path):
                links.add(full_url)
                
        logger.info(f"[kicker/{section}] kept after filters={len(links)}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        # Kicker pagination is often JS-driven ("Mehr laden")
        logger.info("KickerScraper does not support pagination (likely JS-driven).")
        return None