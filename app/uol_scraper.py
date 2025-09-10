"""
UOL-specific scraper implementation
"""

import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
from tenacity import retry, wait_exponential, stop_after_attempt
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class UolScraper(BaseScraper):
    """Scraper specifically designed for UOL news sites"""
    
    def __init__(self, store, request_delay=1.0):
        super().__init__(store, request_delay)
        # Use standard browser User-Agent for UOL to avoid blocking
        self.browser_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.uol.com.br/',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        self.session.headers.update(self.browser_headers)
        
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    def _fetch_page(self, url):
        """Override to use enhanced browser headers for UOL requests"""
        if not self.can_fetch(url):
            logger.warning(f"Robots.txt disallows fetching {url}")
            return None
        
        # Enhanced browser headers for anti-bot protection
        enhanced_headers = {
            **self.browser_headers,
            'sec-ch-ua': '"Chromium";v="91", " Not A;Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'upgrade-insecure-requests': '1',
            'accept-encoding': 'gzip, deflate, br',
            'cache-control': 'max-age=0'
        }
        
        try:
            response = self.session.get(url, headers=enhanced_headers, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                # Try AMP version as fallback
                if '/amp' not in url and '?amp' not in url:
                    try:
                        amp_url = url.rstrip('/') + '/amp'
                        logger.info(f"Trying AMP version: {amp_url}")
                        response = self.session.get(amp_url, headers=enhanced_headers, timeout=15)
                        response.raise_for_status()
                        return response.text
                    except:
                        pass
            logger.error(f"Error fetching {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise
    
    def get_site_domain(self):
        """Return the main domain for UOL"""
        return "uol.com.br"
    
    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from UOL listing pages with section filtering"""
        soup = BeautifulSoup(html, 'lxml')
        links = []
        
        # Section-specific selectors for better filtering
        section_selectors = {
            'futebol': [
                'a[href*="/esporte/futebol/"]',
                'a[href*="/futebol/"]'
            ],
            'economia': [
                'a[href*="economia.uol.com.br"]',
                'a[href*="/play/videos/economia/"]',
                'a[href*="/economia/"]',
                'a[href*="/mercado/"]'
            ],
            'politica': [
                'a[href*="/politica/"]',
                'a[href*="/poder/"]'
            ],
            'mundo': [
                'a[href*="/internacional/"]',
                'a[href*="/mundo/"]'
            ]
        }
        
        # Use section-specific selectors if available, otherwise generic
        if section and section in section_selectors:
            selectors = section_selectors[section]
        else:
            # Fallback to generic selectors
            selectors = [
                'a[href*="/noticias/"]',
                'a[href*="/economia/"]',
                'a[href*="/politica/"]', 
                'a[href*="/internacional/"]',
                'a[href*="/esporte/futebol/"]'
            ]
        
        # Add generic layout selectors
        selectors.extend([
            'h1 a[href]',
            'h2 a[href]',
            'h3 a[href]',
            'h4 a[href]',
            '.manchete a[href]',
            '.chamada a[href]',
            '.card a[href]',
            '.item a[href]',
            '.news-item a[href]',
            '.lista-noticias a[href]',
            '.conteudo-destaque a[href]',
            '.box-noticia a[href]',
            '.destaque a[href]',
            '.thumb-materia a[href]',
            'article a[href]',
            '.artigo a[href]'
        ])
        
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
                    
                    # Filter for UOL news articles with section filtering
                    if self._is_valid_uol_article_url(full_url, section):
                        found_links.add(full_url)
                        
            except Exception as e:
                logger.warning(f"Error with selector {selector}: {e}")
                continue
        
        links = list(found_links)
        logger.info(f"Found {len(links)} article links on UOL page")
        return links
    
    def _is_valid_uol_article_url(self, url, section=None):
        """Check if URL is a valid UOL article with optional section filtering"""
        try:
            parsed = urlparse(url)
            
            # Must be UOL domain (not Folha)
            valid_uol_domains = [
                'www.uol.com.br',
                'economia.uol.com.br', 
                'noticias.uol.com.br',
                'esporte.uol.com.br',
                'play.uol.com.br'
            ]
            
            if not any(domain in parsed.netloc for domain in valid_uol_domains):
                return False
                
            # Explicitly exclude Folha domains
            if 'folha.uol.com.br' in parsed.netloc:
                return False
            
            # Should contain news indicators
            path = parsed.path.lower()
            
            # Section-specific patterns for better filtering
            section_patterns = {
                'futebol': ['/esporte/futebol/', '/futebol/'],
                'economia': ['/economia/', '/mercado/'],
                'politica': ['/politica/', '/poder/'],
                'mundo': ['/internacional/', '/mundo/']
            }
            
            # Special handling for economia section - accept economia subdomain but avoid listing pages
            if section == 'economia' and 'economia.uol.com.br' in parsed.netloc:
                # Exclude home, listing, and non-article pages
                exclude_patterns = [
                    '/busca/', '/arquivo/', '/rss', '/feed', '/ultimas/', '.rss', '.xml',
                    '/$',  # Home page
                    '/temas/', '/podcast/', '/guia-de-', '/cotacoes/', '/empregos-e-carreiras/',
                    '/dinheiro-e-renda/', '/empresas-e-negocios/', '/imposto-de-renda/'
                ]
                # Only accept URLs that look like actual articles (with dates or specific patterns)
                if (any(pattern in path for pattern in exclude_patterns) or 
                    path.count('/') < 2 or  # Too shallow, likely listing page
                    not any(char.isdigit() for char in path)):  # No dates/numbers, likely listing
                    return False
                return True
            
            # Also accept UOL Play economia videos
            if section == 'economia' and 'play.uol.com.br' in parsed.netloc and '/economia/' in path:
                return True
            
            # If section is specified, only allow articles from that section
            if section and section in section_patterns:
                valid_patterns = section_patterns[section]
            else:
                # Fallback to all patterns
                valid_patterns = [
                    '/noticias/',
                    '/economia/',
                    '/politica/',
                    '/internacional/',
                    '/esporte/futebol/',
                    '/mercado/',
                    '/poder/',
                    '/mundo/'
                ]
            
            if any(pattern in path for pattern in valid_patterns):
                # Exclude non-article pages
                exclude_patterns = [
                    '/busca/',
                    '/arquivo/',
                    '/rss',
                    '/feed',
                    '/ultimas/',
                    '.rss',
                    '.xml',
                    '/times/',  # Team pages, not articles
                    '/tabela',  # League tables
                    '/classificacao'  # Standings
                ]
                
                if any(pattern in path for pattern in exclude_patterns):
                    return False
                
                # Additional section-specific exclusions
                if section == 'futebol':
                    # Exclude non-football URLs when scraping football
                    non_football_patterns = ['/politica/', '/economia/', '/internacional/', '/poder/', '/mercado/', '/mundo/']
                    if any(pattern in path for pattern in non_football_patterns):
                        return False
                elif section == 'economia':
                    # Exclude non-economy URLs when scraping economy
                    non_economy_patterns = ['/politica/', '/futebol/', '/internacional/', '/poder/', '/mundo/']
                    if any(pattern in path for pattern in non_economy_patterns):
                        return False
                
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error validating UOL URL {url}: {e}")
            return False
    
    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of UOL articles"""
        soup = BeautifulSoup(html, 'lxml')
        
        # UOL pagination selectors
        next_selectors = [
            'a[rel="next"]',
            '.pagination a[href*="pagina="]',
            '.paginacao a[href*="pagina="]',
            'a[href*="proxima"]',
            'a[href*="next"]',
            '.next a[href]',
            '.proximo a[href]'
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
        
        # Try to find pagination by page numbers
        try:
            # Look for numbered pagination
            page_links = soup.select('a[href*="pagina="], a[href*="page="]')
            if page_links:
                # Get current page number from URL
                from urllib.parse import parse_qs, urlparse
                parsed_current = urlparse(current_url)
                current_params = parse_qs(parsed_current.query)
                current_page = int(current_params.get('pagina', current_params.get('page', ['1']))[0])
                
                # Look for next page
                next_page = current_page + 1
                for link in page_links:
                    href = link.get('href', '')
                    if f'pagina={next_page}' in href or f'page={next_page}' in href:
                        if href.startswith('/'):
                            return urljoin(current_url, href)
                        elif href.startswith('http'):
                            return href
                            
        except Exception as e:
            logger.warning(f"Error finding next page by number: {e}")
        
        return None
    
    def parse_article(self, url, source=None, section=None):
        """Parse UOL article with specific handling"""
        article = super().parse_article(url, source=source, section=section)
        
        if article:
            # Additional UOL-specific processing
            article = self._enhance_uol_metadata(article, url)
        
        return article
    
    def _enhance_uol_metadata(self, article, url):
        """Add UOL-specific metadata enhancements"""
        try:
            # UOL-specific author cleaning
            if article.get('author'):
                author = article['author']
                # Remove common UOL suffixes
                author = author.replace(' - UOL', '')
                author = author.replace('UOL ', '')
                article['author'] = author.strip()
            
            # Extract section from URL for better categorization
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            if len(path_parts) > 1:
                url_section = path_parts[0].lower()
                if url_section in ['economia', 'politica', 'internacional', 'esporte']:
                    article['section'] = url_section
            
            return article
            
        except Exception as e:
            logger.warning(f"Error enhancing UOL metadata for {url}: {e}")
            return article