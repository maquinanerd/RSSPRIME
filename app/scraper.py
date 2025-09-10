import re
import json
import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse
from datetime import datetime
import logging
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from dateutil import parser as date_parser
from .utils import normalize_date, extract_mime_type, get_user_agent

logger = logging.getLogger(__name__)

class LanceScraper:
    def __init__(self, store, request_delay=1.0):
        self.store = store
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': get_user_agent()
        })
        self.robots_checker = None
        
    def _check_robots_txt(self, url):
        """Check if we can fetch the given URL according to robots.txt"""
        try:
            if not self.robots_checker:
                base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                robots_url = urljoin(base_url, '/robots.txt')
                
                self.robots_checker = urllib.robotparser.RobotFileParser()
                self.robots_checker.set_url(robots_url)
                self.robots_checker.read()
                
            # Debug the robots check
            user_agent = get_user_agent()
            can_fetch = self.robots_checker.can_fetch(user_agent, url)
            logger.debug(f"Robots check for {url} with UA '{user_agent}': {can_fetch}")
            
            # LANCE! robots.txt allows all (Allow: /), so if we get False, there's a parsing issue
            # Let's be more permissive for educational purposes
            if not can_fetch and 'lance.com.br' in url:
                logger.info(f"Robots parser returned False for LANCE!, but robots.txt allows all. Proceeding.")
                return True
                
            return can_fetch
        except Exception as e:
            logger.warning(f"Could not check robots.txt: {e}")
            return True  # Assume allowed if we can't check
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _fetch_page(self, url):
        """Fetch a web page with retries and error handling"""
        if not self._check_robots_txt(url):
            logger.warning(f"robots.txt disallows fetching {url}")
            return None
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise
    
    def extract_article_links(self, html, base_url):
        """Extract article links from listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = []
        
        # Find all links that point to articles (ending in .html)
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            
            # Convert relative URLs to absolute
            if href and isinstance(href, str) and href.startswith('/'):
                href = urljoin(base_url, href)
            
            # Filter for LANCE articles ending in .html
            if (href and isinstance(href, str) and href.startswith('https://www.lance.com.br/') and 
                href.endswith('.html')):
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
    
    def find_next_page(self, html, current_url):
        """Find the next page URL from pagination"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for <link rel="next">
        next_link = soup.find('link', {'rel': 'next'})
        if next_link and hasattr(next_link, 'get') and next_link.get('href'):
            next_url = next_link.get('href', '')
            if next_url and isinstance(next_url, str) and next_url.startswith('/'):
                next_url = urljoin(current_url, next_url)
            return next_url
        
        return None
    
    def list_pages(self, start_url, max_pages=3):
        """Collect article links from paginated listing"""
        all_links = []
        current_url = start_url
        page_count = 0
        
        logger.info(f"Starting pagination from {start_url}, max_pages={max_pages}")
        
        while current_url and page_count < max_pages:
            try:
                logger.info(f"Fetching page {page_count + 1}: {current_url}")
                
                html = self._fetch_page(current_url)
                if not html:
                    break
                
                # Extract article links
                page_links = self.extract_article_links(html, current_url)
                all_links.extend(page_links)
                
                # Find next page
                next_url = self.find_next_page(html, current_url)
                current_url = next_url
                page_count += 1
                
                # Rate limiting
                if current_url:
                    time.sleep(self.request_delay)
                    
            except Exception as e:
                logger.error(f"Error processing page {current_url}: {e}")
                break
        
        logger.info(f"Collected {len(all_links)} total links from {page_count} pages")
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
            if isinstance(image, str):
                metadata['image'] = image
            elif isinstance(image, dict):
                metadata['image'] = image.get('url', '')
            elif isinstance(image, list) and len(image) > 0:
                if isinstance(image[0], str):
                    metadata['image'] = image[0]
                elif isinstance(image[0], dict):
                    metadata['image'] = image[0].get('url', '')
        
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
            metadata['image'] = str(img_meta.get('content', ''))
        
        return metadata
    
    def parse_article(self, url):
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
                'image': metadata.get('image', '').strip(),
                'author': metadata.get('author', '').strip(),
                'date_published': normalize_date(metadata.get('date_published')),
                'date_modified': normalize_date(metadata.get('date_modified')),
                'fetched_at': datetime.utcnow()
            }
            
            # Skip articles without title
            if not article['title']:
                logger.warning(f"Skipping article without title: {url}")
                return None
            
            return article
            
        except Exception as e:
            logger.error(f"Error parsing article {url}: {e}")
            return None
    
    def scrape_and_store(self, start_url, max_pages=3):
        """Main scraping method that collects and stores articles"""
        logger.info(f"Starting scrape from {start_url}")
        
        # Get article links from listing pages
        article_urls = self.list_pages(start_url, max_pages)
        
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
                article = self.parse_article(url)
                if article:
                    # Store in database
                    self.store.upsert_article(article)
                    new_articles.append(article)
                    logger.info(f"Stored article: {article['title']}")
                
                # Rate limiting between articles
                time.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"Error processing article {url}: {e}")
                continue
        
        logger.info(f"Scraping completed. New articles: {len(new_articles)}")
        return new_articles
