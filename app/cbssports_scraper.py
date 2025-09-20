import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class CBSSportsScraper(BaseScraper):
    """
    Scraper for CBS Sports (cbssports.com) news.
    """

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "cbssports.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from CBS Sports listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # CBS Sports uses several layouts. We'll try a few common selectors.
        # Selector for main article lists
        for item in soup.select('.article-list-pack-item, .article-list-item-v2'):
            link_tag = item.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                # Filter out non-article links
                if '/video/' not in href and '/live/' not in href:
                    full_url = urljoin(base_url, href)
                    links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        # CBS Sports often uses a "Load More" button driven by JavaScript.
        # A simple scraper can't easily follow this.
        logger.info(
            "CBSSportsScraper does not support pagination (likely JS-driven 'Load More' button)."
        )
        return None