import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


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

        # Kicker uses multiple layouts. We'll try a few common selectors.
        selectors = [
            'a.kick__teaser-link',              # Main teaser links
            'h3.kick__card-headline a',         # Headlines in cards
            'a.kick__v100-Teaser__headlineLink' # Old selector as a fallback
        ]
 
        for selector in selectors:
            for link_tag in soup.select(selector):
                href = link_tag.get('href')
                # Kicker article URLs typically contain /artikel
                if href and '/artikel' in href:
                    # urljoin handles both relative and absolute URLs
                    full_url = urljoin(base_url, href)
                    links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        # Kicker pagination is often JS-driven ("Mehr laden")
        logger.info("KickerScraper does not support pagination (likely JS-driven).")
        return None