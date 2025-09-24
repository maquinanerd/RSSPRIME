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
        """
        Extract article links from Fox Sports listing page HTML or official RSS feed XML.
        """
        # Analisa o XML do feed RSS oficial em vez de raspar o HTML.
        soup = BeautifulSoup(html, 'xml')
        links = set()

        # O feed RSS oficial usa a tag <link> para cada item.
        for item in soup.find_all('item'):
            link_tag = item.find('link')
            if link_tag and link_tag.text:
                url = link_tag.text.strip()
                # Garante que a URL é válida antes de adicionar
                if url.startswith('http'):
                    links.add(url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        # A paginação não é necessária ao consumir um feed RSS direto.
        return None