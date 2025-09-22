import logging
import json
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


OLE_BASE_URL = "https://www.ole.com.ar"
 
def _split_jsonld(raw: str) -> list[str]:
    """
    Some sites concatenate multiple JSON objects in the same <script>.
    This helper heuristically attempts to separate valid JSON blocks.
    """
    out, buf, depth = [], [], 0
    in_str, esc = False, False
    for ch in raw:
        buf.append(ch)
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    out.append(''.join(buf).strip())
                    buf = []
    if not out and raw.strip().startswith('{'):
        out = [raw]
    return out

class OleScraper(BaseScraper):
    """
    Scraper for Ole.com.ar news.
    """

    def __init__(self, store, request_delay=1.0):
        super().__init__(store, request_delay)
        # Use headers recommended for the region to avoid content variations
        self.session.headers.update({
            "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
        })

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "ole.com.ar"

    def extract_article_links(self, html, base_url, section=None):
        """
        Extracts article links from the Olé listing page.
        1. Prioritizes JSON-LD (most reliable).
        2. Falls back to CSS selectors.
        3. Falls back to Regex on raw HTML for embedded JS objects.
        """
        soup = BeautifulSoup(html, 'lxml')
        links = []
        
        # 1. JSON-LD (Primary, robust method)
        try:
            for tag in soup.find_all("script", {"type": "application/ld+json"}):
                raw_json = tag.string or ""
                for blob in _split_jsonld(raw_json):
                    try:
                        data = json.loads(blob)
                        payloads = data if isinstance(data, list) else [data]
                        for obj in payloads:
                            item_lists = []
                            if obj.get("@type") == "CollectionPage":
                                main_entity = obj.get("mainEntity", [])
                                main_entity = [main_entity] if isinstance(main_entity, dict) else main_entity
                                for entity in main_entity:
                                    if entity.get("@type") == "ItemList":
                                        item_lists.append(entity)
                            elif obj.get("@type") == "ItemList":
                                item_lists.append(obj)
                            
                            for item_list in item_lists:
                                elements = item_list.get("itemListElement", [])
                                for li in elements:
                                    if isinstance(li, dict):
                                        url = li.get("url") or (li.get("item") or {}).get("url")
                                        if url:
                                            links.append(url)
                    except json.JSONDecodeError:
                        continue # Ignore malformed JSON blobs
            if links:
                logger.info(f"Successfully extracted {len(links)} links via JSON-LD from {base_url}")
        except Exception as e:
            logger.debug(f"[ole] JSON-LD parsing step failed: {e}")

        # 2. CSS Fallback
        if not links:
            logger.info("JSON-LD failed, trying CSS selectors fallback.")
            selectors = [
                'article a[href$=".html"]',
                '.card a[href$=".html"]',
                '.mod-note a[href$=".html"]',
                'a[href^="/"][href$=".html"]',
            ]
            for sel in selectors:
                for a_tag in soup.select(sel):
                    href = a_tag.get("href")
                    if href:
                        links.append(href)
            if links:
                logger.info(f"Extracted {len(links)} links via CSS from {base_url}")

        # 3. Regex Fallback for embedded JS
        if not links:
            logger.info("CSS selectors failed, trying Regex fallback for embedded JS.")
            pattern = r'"url"\s*:\s*"((?:https:\/\/www\.ole\.com\.ar)?\/[^"]+?\.html)"'
            for match in re.finditer(pattern, html):
                links.append(match.group(1))
            if links:
                logger.info(f"Extracted {len(links)} links via Regex from {base_url}")

        # Normalization, Deduplication, and Filtering
        seen = set()
        final_links = []
        for link in links:
            full_url = urljoin(OLE_BASE_URL, link)
            if 'ole.com.ar' in full_url and full_url.endswith(".html") and '/videos/' not in full_url:
                if full_url not in seen:
                    seen.add(full_url)
                    final_links.append(full_url)

        logger.info(f"Extracted {len(final_links)} unique article links from {base_url} for section '{section}'")
        if not final_links:
            logger.warning(f"No article links found for ole/{section} on page {base_url}")
            
        return final_links

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        logger.info("OleScraper does not support pagination.")
        return None