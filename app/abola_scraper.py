import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ABolaScraper(BaseScraper):
    """
    Scraper for A Bola news.
    """

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "abola.pt"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from A Bola listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        for link_tag in soup.select('a.text-dark-blue'):
            href = link_tag.get('href')
            if href and href.startswith('/nnh/'):
                links.add(urljoin(base_url, href))

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        return None