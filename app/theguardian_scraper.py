import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class TheGuardianScraper(BaseScraper):
    """
    Scraper for The Guardian news.
    """

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "theguardian.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from The Guardian listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # The Guardian uses a consistent data-link-name attribute for articles
        for link_tag in soup.select('a[data-link-name="article"]'):
            href = link_tag.get('href')
            if href and href.startswith('http'):
                links.add(href)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """The Guardian uses numbered pagination links."""
        soup = BeautifulSoup(html, 'lxml')
        next_link = soup.select_one('a[rel="next"]')
        if next_link and next_link.get('href'):
            return urljoin(current_url, next_link['href'])
        return None

    def apply_filters(self, article: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        return False