"""
Base scraper class that defines the interface for all news site scrapers
"""

import logging
import requests
import json
from urllib.robotparser import RobotFileParser
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from .utils import normalize_date, extract_mime_type, get_user_agent

logger = logging.getLogger(__name__)

def _should_retry_http_request(exception: BaseException) -> bool:
    """
    Predicate for tenacity to decide if a request should be retried.
    Retries on:
    - 5xx server errors.
    - Specific 4xx errors (408 Request Timeout, 429 Too Many Requests).
    - General connection errors or timeouts.
    Does NOT retry on other 4xx client errors (e.g., 404, 403, 406).
    """
    if isinstance(exception, requests.exceptions.HTTPError):
        status_code = exception.response.status_code
        return status_code >= 500 or status_code in [408, 429]
    elif isinstance(exception, requests.exceptions.RequestException):
        return True  # Includes ConnectionError, Timeout, etc.
    return False

def clean_image_url(url: str) -> str:
    """Clean image URL by removing CDN optimization parameters"""
    if not url:
        return url
    
    if "/uploads/" in url:
        # Extract the host from the original URL
        if url.startswith('http'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = f"{parsed.scheme}://{parsed.netloc}"
        else:
            host = "https://lncimg.lance.com.br"
        
        # Keep the host + path from /uploads/
        uploads_part = url.split("/uploads/", 1)[-1]
        return f"{host}/uploads/{uploads_part}"
    
    return url

class BaseScraper(ABC):
    """Abstract base class for all news site scrapers"""
    
    def __init__(self, store, request_delay=1.0):
        self.store = store
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': get_user_agent()})
        self.robots_cache = {}
    
    @abstractmethod
    def get_site_domain(self):
        """Return the main domain for this scraper"""
        pass
    
    @abstractmethod
    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from a listing page HTML"""
        pass
    
    @abstractmethod
    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        pass
    
    def apply_filters(self, article, filters):
        """Apply filters to an article and return True if article should be excluded"""
        if not filters:
            return False
            
        try:
            # Check exclude_authors filter
            if filters.get('exclude_authors'):
                author = article.get('author', '').lower()
                for excluded_author in filters['exclude_authors']:
                    if excluded_author.lower() in author:
                        logger.debug(f"Excluding article by author: {author}")
                        return True
            
            # Check exclude_terms filter  
            if filters.get('exclude_terms'):
                title = article.get('title', '').lower()
                description = article.get('description', '').lower()
                
                for term in filters['exclude_terms']:
                    term_lower = term.lower()
                    if term_lower in title or term_lower in description:
                        logger.debug(f"Excluding article containing term: {term}")
                        return True
            
            return False  # Article should be included
            
        except Exception as e:
            logger.warning(f"Error applying filters: {e}")
            return False  # Include article if filter evaluation fails
    
    def can_fetch(self, url):
        """Check if we can fetch the URL according to robots.txt"""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            
            if domain not in self.robots_cache:
                robots_url = f"https://{domain}/robots.txt"
                rp = RobotFileParser()
                rp.set_url(robots_url)
                try:
                    rp.read()
                    self.robots_cache[domain] = rp
                except Exception as e:
                    logger.warning(f"Could not read robots.txt for {domain}: {e}")
                    # If we can't read robots.txt, assume we can fetch
                    self.robots_cache[domain] = None
            
            rp = self.robots_cache[domain]
            if rp is None:
                return True
            
            user_agent = self.session.headers.get('User-Agent', get_user_agent())
            can_fetch = rp.can_fetch(user_agent, url)
            
            logger.debug(f"Robots check for {url} with UA '{user_agent[:50]}...': {can_fetch}")
            
            # If robots.txt says no but we know the site allows scraping, proceed with caution
            if not can_fetch:
                logger.info(f"Robots parser returned False for {self.get_site_domain()}, but robots.txt allows all. Proceeding.")
            
            return True  # We generally allow scraping for news sites
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True
    
    @retry(
        stop=stop_after_attempt(2), 
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception(_should_retry_http_request)
    )
    def _fetch_page(self, url):
        """Fetch a single page with retries (optimized for performance)"""
        if not self.can_fetch(url):
            logger.warning(f"Robots.txt disallows fetching {url}")
            return None
        
        try:
            response = self.session.get(url, timeout=15)  # Reduced timeout
            response.raise_for_status()
            response.encoding = 'utf-8'
            content = response.text
            logger.debug(f"Fetched {url} - Status: {response.status_code}, Length: {len(content)} bytes")
            return content
        except requests.exceptions.RequestException as e:
            # This will be caught by tenacity and retried based on _should_retry_http_request
            logger.error(f"Request error fetching {url}: {e}")
            raise
    
    def list_pages(self, start_url, max_pages=3, section=None):
        """Get article links from multiple pages starting from start_url"""
        all_links = []
        current_url = start_url
        
        for page_num in range(max_pages):
            try:
                logger.info(f"Fetching page {page_num + 1}: {current_url}")
                html = self._fetch_page(current_url)
                
                if not html:
                    logger.warning(f"No content received from {current_url}")
                    break
                
                # Extract article links from current page
                page_links = self.extract_article_links(html, current_url, section=section)
                if not page_links:
                    logger.warning(f"No article links found on page {page_num + 1}")
                    break
                
                all_links.extend(page_links)
                logger.info(f"Found {len(page_links)} article links on page {page_num + 1}")
                
                # Find next page URL
                if page_num < max_pages - 1:
                    next_url = self.find_next_page_url(html, current_url)
                    if not next_url or next_url == current_url:
                        logger.info("No more pages found")
                        break
                    current_url = next_url
                
                # Delay between requests
                if self.request_delay > 0:
                    import time
                    time.sleep(self.request_delay)
                    
            except Exception as e:
                logger.error(f"Error processing page {page_num + 1} ({current_url}): {e}")
                break
        
        logger.info(f"Total article links collected: {len(all_links)}")
        return all_links
    
    def parse_json_ld(self, html):
        """Extract JSON-LD metadata from article page"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Find all JSON-LD scripts
        scripts = soup.find_all('script', {'type': 'application/ld+json'})
        
        for script in scripts:
            try:
                script_content = getattr(script, 'string', None) or ''
                if not script_content or not isinstance(script_content, str):
                    continue
                data = json.loads(script_content)
                
                # Handle different JSON-LD structures
                items = []
                
                if isinstance(data, dict):
                    if '@graph' in data:
                        items = data['@graph']
                    else:
                        items = [data]
                elif isinstance(data, list):
                    items = data
                
                # Look for Article/NewsArticle/BlogPosting
                for item in items:
                    if isinstance(item, dict):
                        item_type = item.get('@type', '')
                        if item_type in ['Article', 'NewsArticle', 'BlogPosting']:
                            return self._extract_article_metadata(item)
                            
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error parsing JSON-LD: {e}")
                continue
        
        return None
    
    def _extract_article_metadata(self, json_ld):
        """Extract article metadata from JSON-LD object"""
        metadata = {}
        
        # Title/headline
        metadata['title'] = json_ld.get('headline', json_ld.get('name', ''))
        
        # Description
        metadata['description'] = json_ld.get('description', '')
        
        # Image
        image = json_ld.get('image')
        if image:
            raw_image_url = ''
            if isinstance(image, str):
                raw_image_url = image
            elif isinstance(image, dict):
                raw_image_url = image.get('url', '')
            elif isinstance(image, list) and len(image) > 0:
                if isinstance(image[0], str):
                    raw_image_url = image[0]
                elif isinstance(image[0], dict):
                    raw_image_url = image[0].get('url', '')
            
            # Clean the image URL
            metadata['image'] = clean_image_url(raw_image_url)
        
        # Dates
        metadata['date_published'] = json_ld.get('datePublished', '')
        metadata['date_modified'] = json_ld.get('dateModified', '')
        
        # Author
        author = json_ld.get('author')
        if author:
            if isinstance(author, str):
                metadata['author'] = author
            elif isinstance(author, dict):
                metadata['author'] = author.get('name', '')
            elif isinstance(author, list) and len(author) > 0:
                if isinstance(author[0], str):
                    metadata['author'] = author[0]
                elif isinstance(author[0], dict):
                    metadata['author'] = author[0].get('name', '')
        
        return metadata
    
    def extract_fallback_metadata(self, html, url):
        """Extract fallback metadata from HTML meta tags"""
        soup = BeautifulSoup(html, 'lxml')
        metadata = {}
        
        # Title fallback
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()
        
        # Description fallback
        desc_meta = soup.find('meta', {'name': 'description'}) or \
                   soup.find('meta', {'property': 'og:description'})
        if desc_meta and hasattr(desc_meta, 'get') and desc_meta.get('content'):
            metadata['description'] = str(desc_meta.get('content', ''))
        
        # Image fallback
        img_meta = soup.find('meta', {'property': 'og:image'})
        if img_meta and hasattr(img_meta, 'get') and img_meta.get('content'):
            raw_image_url = str(img_meta.get('content', ''))
            metadata['image'] = clean_image_url(raw_image_url)
        
        return metadata
    
    def parse_article(self, url, source=None, section=None):
        """Parse individual article and extract metadata"""
        try:
            html = self._fetch_page(url)
            if not html:
                return None
            
            # Try JSON-LD first
            metadata = self.parse_json_ld(html)
            
            # Fallback to HTML meta tags
            if not metadata or not metadata.get('title'):
                fallback = self.extract_fallback_metadata(html, url)
                if not metadata:
                    metadata = fallback
                else:
                    # Merge fallback data for missing fields
                    for key, value in fallback.items():
                        if not metadata.get(key):
                            metadata[key] = value
            
            if not metadata:
                return None
            
            # Normalize the article data
            article = {
                'url': url,
                'title': metadata.get('title', '').strip(),
                'description': metadata.get('description', '').strip(),
                'image': clean_image_url(metadata.get('image', '').strip()),
                'author': metadata.get('author', '').strip(),
                'date_published': normalize_date(metadata.get('date_published')),
                'date_modified': normalize_date(metadata.get('date_modified')),
                'fetched_at': datetime.now(timezone.utc),
                'source': source or 'unknown',
                'section': section or 'general',
                'site': self.get_site_domain()
            }
            
            # Skip articles without title
            if not article['title']:
                logger.warning(f"Skipping article without title: {url}")
                return None
            
            return article
            
        except Exception as e:
            logger.error(f"Error parsing article {url}: {e}")
            return None
    
    def scrape_and_store(self, start_urls, max_pages=3, source=None, section=None, filters=None):
        """Main scraping method that collects and stores articles"""
        # Handle both single URL and list of URLs
        if isinstance(start_urls, str):
            start_urls = [start_urls]
        
        logger.info(f"Starting scrape from {len(start_urls)} source(s): {start_urls}")
        
        # Get article links from all listing pages
        all_article_urls = []
        for start_url in start_urls:
            logger.info(f"Scraping from: {start_url}")
            article_urls = self.list_pages(start_url, max_pages)
            all_article_urls.extend(article_urls)
        
        # Remove duplicates while preserving order
        seen = set()
        article_urls = []
        for url in all_article_urls:
            if url not in seen:
                seen.add(url)
                article_urls.append(url)
        
        if not article_urls:
            logger.warning("No article URLs found")
            return []
        
        # Process each article
        new_articles = []
        for i, url in enumerate(article_urls):
            try:
                logger.info(f"Processing article {i+1}/{len(article_urls)}: {url}")
                
                # Check if we already have this article
                if self.store.has_article(url):
                    logger.debug(f"Article already exists: {url}")
                    continue
                
                # Parse article
                article = self.parse_article(url, source=source, section=section)
                if not article:
                    logger.warning(f"Could not parse article: {url}")
                    continue
                
                # Apply filters
                if filters and self._should_filter_article(article, filters):
                    logger.info(f"Article filtered out: {url}")
                    continue
                
                # Store article
                if self.store.upsert_article(article):
                    new_articles.append(article)
                    logger.info(f"Stored article: {article['title']}")
                
                # Delay between requests
                if self.request_delay > 0:
                    import time
                    time.sleep(self.request_delay)
                    
            except Exception as e:
                logger.error(f"Error processing article {url}: {e}")
                continue
        
        logger.info(f"Scraping completed. New articles: {len(new_articles)}")
        return new_articles
    
    def _should_filter_article(self, article, filters):
        """Check if article should be filtered out based on filter rules"""
        if not filters:
            return False
        
        # Filter by excluded authors
        exclude_authors = filters.get('exclude_authors', [])
        if exclude_authors and article.get('author'):
            author = article['author'].lower()
            for excluded in exclude_authors:
                if excluded.lower() in author:
                    return True
        
        return False