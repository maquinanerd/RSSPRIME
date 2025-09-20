import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GazetaScraper(BaseScraper):
    """
    Scraper for Gazeta Esportiva news.
    This is a placeholder implementation.
    """

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "gazetaesportiva.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Gazeta Esportiva listing page HTML"""
        logger.warning(
            f"GazetaScraper.extract_article_links is not implemented for {base_url}. Returning empty list."
        )
        return []

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        logger.info("GazetaScraper does not support pagination.")
        return None