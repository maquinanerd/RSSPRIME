"""
Scraper for Ole.com.ar
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class OleScraper(BaseScraper):
    """Scraper for Ole.com.ar"""

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "ole.com.ar"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Ole listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Links are in <a> tags with class 'link-off'
        for link_tag in soup.find_all('a', class_='link-off', href=True):
            href = link_tag['href']
            full_url = urljoin(base_url, href)
            # Ensure it's an article and not a tag page etc.
            if any(s in full_url for s in ['/futbol-primera/', '/futbol-ascenso/']) and full_url.endswith('.html'):
                links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the next page URL from pagination"""
        soup = BeautifulSoup(html, 'lxml')
        next_link = soup.select_one('a.pagination__arrow--right[href]')
        if next_link:
            return urljoin(current_url, next_link['href'])
        return None