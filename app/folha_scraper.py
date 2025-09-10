"""
Folha de S.Paulo-specific scraper implementation
"""

import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class FolhaScraper(BaseScraper):
    """Scraper specifically designed for Folha de S.Paulo news sites"""
    
    def get_site_domain(self):
        """Return the main domain for Folha"""
        return "folha.uol.com.br"
    
    def extract_article_links(self, html, base_url):
        """Extract article links from Folha listing pages"""
        soup = BeautifulSoup(html, 'lxml')
        links = []
        
        # Folha uses specific structures for different sections
        selectors = [
            # Main article links
            'a[href*="/poder/"]',
            'a[href*="/mercado/"]',
            'a[href*="/mundo/"]',
            'a[href*="/politica/"]',
            'a[href*="/economia/"]',
            # Generic news links
            'h2 a[href]',
            'h3 a[href]',
            'h4 a[href]',
            '.c-headline a[href]',
            '.c-main-headline a[href]',
            # Card and list layouts
            '.c-news-item a[href]',
            '.u-list-unstyled a[href]',
            '.c-feed__content a[href]',
            # Time-based listings
            '.c-latest-news a[href]'
        ]
        
        found_links = set()
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get('href')
                    if not href:
                        continue
                    
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        full_url = urljoin(base_url, href)
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    # Filter for Folha news articles
                    if self._is_valid_folha_article_url(full_url):
                        found_links.add(full_url)
                        
            except Exception as e:
                logger.warning(f"Error with selector {selector}: {e}")
                continue
        
        links = list(found_links)
        logger.info(f"Found {len(links)} article links on Folha page")
        return links
    
    def _is_valid_folha_article_url(self, url):
        """Check if URL is a valid Folha article"""
        try:
            parsed = urlparse(url)
            
            # Must be Folha domain
            if 'folha.uol.com.br' not in parsed.netloc:
                return False
            
            # Should contain news indicators
            path = parsed.path.lower()
            
            # Valid patterns for Folha articles
            valid_patterns = [
                '/poder/',
                '/mercado/',
                '/mundo/',
                '/politica/',
                '/economia/',
                '/cotidiano/',
                '/esporte/',
                '/ilustrada/'
            ]
            
            if any(pattern in path for pattern in valid_patterns):
                # Exclude non-article pages
                exclude_patterns = [
                    '/busca/',
                    '/arquivo/',
                    '/rss',
                    '/feed',
                    '/newsletter',
                    '.rss',
                    '.xml',
                    '/blogs/',
                    '/colunistas/'
                ]
                
                if any(pattern in path for pattern in exclude_patterns):
                    return False
                
                # Folha articles usually have dates in URL or are in news sections
                if (any(pattern in path for pattern in valid_patterns) and 
                    (len(path.split('/')) >= 3)):  # Proper article structure
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error validating Folha URL {url}: {e}")
            return False
    
    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of Folha articles"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Folha pagination selectors
        next_selectors = [
            'a[rel="next"]',
            '.c-pagination a[href*="page="]',
            '.pagination a[href*="pagina="]',
            'a[href*="proxima"]',
            'a[href*="next"]',
            '.next a[href]',
            '.proximo a[href]',
            '.c-pagination__next[href]'
        ]
        
        for selector in next_selectors:
            try:
                next_link = soup.select_one(selector)
                if next_link and next_link.get('href'):
                    href = next_link.get('href')
                    
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        return urljoin(current_url, href)
                    elif href.startswith('http'):
                        return href
                        
            except Exception as e:
                logger.warning(f"Error finding next page with selector {selector}: {e}")
                continue
        
        # Try to find "Load More" or infinite scroll patterns
        try:
            load_more_selectors = [
                'button[data-load-more]',
                '.load-more[href]',
                '.c-load-more[href]',
                '[data-next-page]'
            ]
            
            for selector in load_more_selectors:
                element = soup.select_one(selector)
                if element:
                    # For Folha, this might be AJAX-based, so we'll skip for now
                    logger.info("Found load-more button, but skipping AJAX pagination")
                    break
                    
        except Exception as e:
            logger.warning(f"Error finding load-more elements: {e}")
        
        return None
    
    def parse_article(self, url, source=None, section=None):
        """Parse Folha article with specific handling"""
        article = super().parse_article(url, source=source, section=section)
        
        if article:
            # Additional Folha-specific processing
            article = self._enhance_folha_metadata(article, url)
        
        return article
    
    def _enhance_folha_metadata(self, article, url):
        """Add Folha-specific metadata enhancements"""
        try:
            # Folha-specific author cleaning
            if article.get('author'):
                author = article['author']
                # Remove common Folha suffixes
                author = author.replace(' - Folha', '')
                author = author.replace('Folha ', '')
                author = author.replace(' da Folha', '')
                article['author'] = author.strip()
            
            # Extract section from URL for better categorization
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            if len(path_parts) > 1:
                url_section = path_parts[0].lower()
                if url_section in ['poder', 'mercado', 'mundo', 'cotidiano', 'esporte']:
                    # Map Folha sections to standard names
                    section_mapping = {
                        'poder': 'politica',
                        'mercado': 'economia',
                        'mundo': 'mundo',
                        'cotidiano': 'geral',
                        'esporte': 'esporte'
                    }
                    article['section'] = section_mapping.get(url_section, url_section)
            
            # Clean up description from Folha-specific patterns
            if article.get('description'):
                desc = article['description']
                # Remove "Leia mais" and similar patterns
                desc = desc.replace('Leia mais...', '').replace('Continuar lendo', '')
                desc = desc.replace('Saiba mais', '').strip()
                article['description'] = desc
            
            return article
            
        except Exception as e:
            logger.warning(f"Error enhancing Folha metadata for {url}: {e}")
            return article