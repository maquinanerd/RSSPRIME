"""
Globo Esporte (ge.globo.com) scraper

Scrapes sports news from Globo Esporte portal, including:
- General sports news 
- Futebol (football/soccer)
- Brasileirão coverage
- Team-specific news
"""

import logging
import re
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .utils import normalize_date

logger = logging.getLogger(__name__)

class GloboScraper(BaseScraper):
    """Scraper for Globo Esporte (ge.globo.com)"""
    
    def get_site_domain(self):
        return "ge.globo.com"
    
    def get_section_url(self, section):
        """Get the URL for a specific section"""
        section_urls = {
            'geral': 'https://ge.globo.com/',
            'futebol': 'https://ge.globo.com/futebol/',
            'brasileirao': 'https://ge.globo.com/futebol/brasileirao-serie-a/',
            'libertadores': 'https://ge.globo.com/futebol/copa-libertadores/',
            'internacional': 'https://ge.globo.com/futebol/futebol-internacional/',
            'times': 'https://ge.globo.com/futebol/',
            'combate': 'https://ge.globo.com/combate/',
            'olimpiadas': 'https://ge.globo.com/olimpiadas/'
        }
        
        return section_urls.get(section, section_urls['geral'])
    
    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Globo Esporte pages"""
        links = []
        soup = BeautifulSoup(html, 'lxml')
        seen = set()
        
        # Look for article links with various patterns used by Globo Esporte
        selectors = [
            'a[href*="/noticia/"]',  # News articles
            'a[href*="/futebol/"]',  # Football articles
            'h2 a[href*="ge.globo.com"]',  # Headlines
            'h3 a[href*="ge.globo.com"]',  # Sub-headlines
            '.card-content a[href*="/noticia/"]',  # Card links
            '.feed-item a[href*="/noticia/"]',  # Feed items
            '.manchete a[href*="/noticia/"]',  # Main news
            '.destaque a[href*="/noticia/"]'  # Featured news
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                href = element.get('href')
                if href and self._is_valid_article_url(href, section):
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        full_url = f"https://ge.globo.com{href}"
                    elif not href.startswith('http'):
                        full_url = urljoin(base_url, href)
                    else:
                        full_url = href
                    
                    # Deduplicate using set for O(1) lookup
                    if full_url not in seen:
                        links.append(full_url)
                        seen.add(full_url)
        
        logger.info(f"Found {len(links)} article links on page")
        return links
    
    def _is_valid_article_url(self, url, section=None):
        """Check if URL is a valid Globo Esporte article for the specified section"""
        if not url:
            return False
        
        # Must contain /noticia/ for actual articles
        if '/noticia/' not in url:
            return False
        
        # Must be from ge.globo.com domain
        if 'ge.globo.com' not in url and not url.startswith('/'):
            return False
        
        # Exclude unwanted URLs
        exclude_patterns = [
            '/videos/',
            '/ao-vivo/',
            '/especial/',
            '/interativos/',
            '/placar/',
            '/classificacao/',
            'javascript:',
            'mailto:',
            '#'
        ]
        
        for pattern in exclude_patterns:
            if pattern in url:
                return False
        
        # Apply section-specific filtering
        if section:
            section_patterns = {
                'brasileirao': ['/futebol/brasileirao-serie-a/'],
                'libertadores': ['/futebol/libertadores/'],
                'internacional': ['/futebol/futebol-internacional/'],
                'futebol': ['/futebol/'],
                'geral': []  # Allow all valid articles for general section
            }
            
            allowed_patterns = section_patterns.get(section, [])
            
            # For non-general sections, check if URL matches any allowed pattern
            if section != 'geral' and allowed_patterns:
                url_matches_section = any(pattern in url for pattern in allowed_patterns)
                if not url_matches_section:
                    return False
            
            # Additional exclusions for futebol section to avoid mixing with other sports
            if section == 'futebol':
                futebol_exclusions = [
                    '/motor/',
                    '/olimpiadas/',
                    '/surfe/',
                    '/volei/',
                    '/basquete/',
                    '/tenis/',
                    '/combate/'
                ]
                for exclusion in futebol_exclusions:
                    if exclusion in url:
                        return False
        
        return True
    
    
    def find_next_page_url(self, html, current_url):
        """Find next page URL for pagination"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for pagination links using supported methods
        # Try rel="next" first (most reliable)
        next_link = soup.select_one('a[rel="next"]')
        if next_link and next_link.get('href'):
            href = next_link.get('href')
            return self._make_absolute_url(href, current_url)
        
        # Try class-based selectors
        next_selectors = [
            'a.next',
            'a[href*="pagina-"]',
            '.pagination a.next',
            '.paginacao a.next'
        ]
        
        for selector in next_selectors:
            try:
                next_link = soup.select_one(selector)
                if next_link and next_link.get('href'):
                    href = next_link.get('href')
                    return self._make_absolute_url(href, current_url)
            except Exception as e:
                logger.debug(f"Error checking selector {selector}: {e}")
        
        # Look for links by text content (proper BeautifulSoup way)
        potential_next_links = soup.find_all('a', href=True)
        for link in potential_next_links:
            text = link.get_text(strip=True).lower()
            if any(keyword in text for keyword in ['próxima', 'próximo', 'ver mais', 'mais notícias', 'carregar mais', '>']):
                href = link.get('href')
                if href:
                    return self._make_absolute_url(href, current_url)
        
        return None
    
    
    
    
    
    
    
    
    def _make_absolute_url(self, url, base_url):
        """Convert relative URL to absolute"""
        if not url:
            return None
        
        if url.startswith('http'):
            return url
        elif url.startswith('//'):
            return f"https:{url}"
        elif url.startswith('/'):
            return f"https://ge.globo.com{url}"
        else:
            return urljoin(base_url, url)