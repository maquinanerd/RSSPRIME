
"""
Gazeta Esportiva scraper compatible with the multi-source system
"""

import logging
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_scraper import BaseScraper
from .utils import get_user_agent

logger = logging.getLogger(__name__)

class GazetaScraper(BaseScraper):
    """Scraper specifically designed for Gazeta Esportiva"""
    
    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return 'gazetaesportiva.com'
    
    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = []

        # Find all links that point to articles
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')

            # Convert relative URLs to absolute
            if href and isinstance(href, str) and href.startswith('/'):
                href = urljoin(base_url, href)

            # Filter for Gazeta articles (excluding external links and non-article pages)
            if (href and isinstance(href, str) and 
                href.startswith('https://www.gazetaesportiva.com/') and 
                not href.endswith('/') and
                '/' in href.split('gazetaesportiva.com/')[-1] and
                not any(x in href for x in ['#', '?page=', '/categoria/', '/tag/', '/autor/'])):
                links.append(href)

        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)

        logger.info(f"Extracted {len(unique_links)} article links from {base_url}")
        return unique_links

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        soup = BeautifulSoup(html, 'lxml')

        # Look for pagination links
        next_link = soup.find('a', {'class': 'next'}) or \
                   soup.find('a', string=lambda text: text and 'próxima' in text.lower()) or \
                   soup.find('a', string=lambda text: text and 'next' in text.lower())
        
        if next_link and hasattr(next_link, 'get') and next_link.get('href'):
            next_url = next_link.get('href', '')
            if next_url and isinstance(next_url, str):
                if next_url.startswith('/'):
                    next_url = urljoin(current_url, next_url)
                return next_url

        # Look for numbered pagination
        page_links = soup.find_all('a', href=True)
        current_page = 1
        
        # Try to extract current page from URL
        if '?page=' in current_url:
            try:
                current_page = int(current_url.split('?page=')[-1].split('&')[0])
            except:
                pass
        
        # Look for next page number
        for link in page_links:
            href = link.get('href', '')
            if f'?page={current_page + 1}' in href:
                if href.startswith('/'):
                    href = urljoin(current_url, href)
                return href

        return None
