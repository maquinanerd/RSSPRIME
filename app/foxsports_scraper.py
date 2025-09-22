import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class FoxSportsScraper(BaseScraper):
    """
    Scraper for Fox Sports news.
    """

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "foxsports.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Fox Sports listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        for link_tag in soup.select('div.article-image a'):
            href = link_tag.get('href')
            if href:
                links.add(urljoin(base_url, href))

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        return None