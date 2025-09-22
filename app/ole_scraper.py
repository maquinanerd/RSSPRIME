import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class OleScraper(BaseScraper):
    """
    Scraper for Ole.com.ar news.
    """

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "ole.com.ar"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Ole listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # The main article links are <a> tags with the class 'article-card'
        for link_tag in soup.select('a.article-card'):
            href = link_tag.get('href')
            if href and href.endswith('.html'):
                full_url = urljoin(base_url, href)
                links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        logger.info("OleScraper does not support pagination.")
        return None