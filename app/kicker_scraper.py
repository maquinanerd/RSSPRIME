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

        for link_tag in soup.select('a.kick__v100-Teaser__headlineLink'):
            href = link_tag.get('href')
            if href:
                links.add(urljoin(base_url, href))

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        return None