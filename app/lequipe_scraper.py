import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class LEquipeScraper(BaseScraper):
    """
    Scraper for L'Équipe news.
    """

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "lequipe.fr"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from L'Équipe listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # L'Équipe uses various layouts. Try a few selectors.
        selectors = [
            'a.Article__link',          # Old selector as a fallback
            'a[data-io-article-url]',   # Common for tracking links
            '.MediaTeaser__title a',    # Teaser titles
            'a.Teaser__link',           # Another teaser link variant
        ]

        for selector in selectors:
            for link_tag in soup.select(selector):
                href = link_tag.get('href')
                # Articles usually end with .html
                if href and href.endswith('.html') and '/videos/' not in href and '/diaporama/' not in href:
                    links.add(urljoin(base_url, href))

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        return None