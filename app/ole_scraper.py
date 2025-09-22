import logging
import json
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .utils import normalize_date
from datetime import datetime

logger = logging.getLogger(__name__)


OLE_BASE_URL = "https://www.ole.com.ar"
 
BLACKLIST_SUBSTR = (
    "/suscripciones/", "/estadisticas/", "/agenda/", "/home.html",
    "/resultados/", "/fixture/", "/posiciones/", "/en-vivo/",
)
BLACKLIST_SECTIONS = (
    "/autos/", "/running/", "/tenis/", "/basquet/", "/rugby/", "/voley/",
    "/polideportivo/", "/seleccion/", "/juegos-olimpicos/", "/esports/", "/hockey/",
)

def _is_valid_ole_article_url(url: str) -> bool:
    """Checks if a URL is a candidate for a valid Olé news article."""
    if not url.endswith(".html") or "ole.com.ar" not in url:
        return False
    if any(s in url for s in BLACKLIST_SUBSTR) or any(s in url for s in BLACKLIST_SECTIONS):
        return False
    return True

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
        raw_links = []
        source_method = "None"

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
                                            raw_links.append(url)
                    except json.JSONDecodeError:
                        continue # Ignore malformed JSON blobs
            if raw_links:
                source_method = "JSON-LD"
                logger.info(f"Found {len(raw_links)} raw links via JSON-LD.")
        except Exception as e:
            logger.debug(f"[ole] JSON-LD parsing step failed: {e}")

        # 2. CSS Fallback
        if not raw_links:
            logger.info("JSON-LD failed or found no links, trying CSS selectors fallback.")
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
                        raw_links.append(href)
            if raw_links:
                source_method = "CSS"
                logger.info(f"Found {len(raw_links)} raw links via CSS fallback.")

        # 3. Regex Fallback for embedded JS
        if not raw_links:
            logger.info("CSS selectors failed, trying Regex fallback for embedded JS.")
            pattern = r'"url"\s*:\s*"((?:https:\/\/www\.ole\.com\.ar)?\/[^"]+?\.html)"'
            for match in re.finditer(pattern, html):
                raw_links.append(match.group(1))
            if raw_links:
                source_method = "Regex"
                logger.info(f"Found {len(raw_links)} raw links via Regex fallback.")

        # Normalization, Deduplication, and Filtering
        seen = set()
        final_links = []
        
        # First, deduplicate and normalize
        deduped_normalized_links = []
        for link in raw_links:
            full_url = urljoin(OLE_BASE_URL, link)
            if full_url not in seen:
                seen.add(full_url)
                deduped_normalized_links.append(full_url)
        
        unfiltered_count = len(deduped_normalized_links)

        # Then, filter based on blacklists
        for url in deduped_normalized_links:
            if _is_valid_ole_article_url(url):
                final_links.append(url)
        
        filtered_count = unfiltered_count - len(final_links)
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} blacklisted/invalid URLs during listing.")

        logger.info(f"Extracted {len(final_links)} unique and valid article links from {base_url} for section '{section}' (using {source_method}).")
        if not final_links:
            logger.warning(f"No article links found for ole/{section} on page {base_url}")
            
        return final_links

    def parse_article(self, url: str, source: str | None = None, section: str | None = None) -> dict | None:
        """
        Parses an Olé article, with strict validation for type and section.
        """
        try:
            html = self._fetch_page(url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, "lxml")

            # --- Validation ---
            url_lower = url.lower()
            if not _is_valid_ole_article_url(url):
                logger.warning(f"Discarding article: URL is blacklisted. URL: {url}")
                return None

            is_article_type = False
            is_correct_section = section not in ['primera', 'ascenso']

            for tag in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(tag.string or "{}")
                    payloads = data if isinstance(data, list) else [data]
                    for obj in payloads:
                        if obj.get("@type") in ("Article", "NewsArticle"):
                            is_article_type = True
                            art_sec = obj.get("articleSection")
                            if section in ['primera', 'ascenso']:
                                if isinstance(art_sec, str) and section in art_sec.lower():
                                    is_correct_section = True
                                if isinstance(art_sec, list) and any(section in s.lower() for s in art_sec if isinstance(s, str)):
                                    is_correct_section = True
                except Exception:
                    continue

            # Heuristics if JSON-LD validation failed
            if not is_correct_section:
                if section == 'primera':
                    if "/futbol-primera/" in url_lower:
                        is_correct_section = True
                    primera_clubs = ("/river-plate/", "/boca-juniors/", "/san-lorenzo/",
                                     "/independiente/", "/racing-club/", "/estudiantes-lp/", "/talleres/",
                                     "/gimnasia-lp/", "/argentinos-juniors/", "/rosario-central/")
                    if any(s in url_lower for s in primera_clubs):
                        is_correct_section = True
                elif section == 'ascenso':
                    if "/futbol-ascenso/" in url_lower:
                        is_correct_section = True

            if not is_article_type:
                logger.warning(f"Discarding article: Not a valid article type (Article/NewsArticle). URL: {url}")
                return None
            if not is_correct_section:
                logger.warning(f"Discarding article: Section mismatch for '{section}'. URL: {url}")
                return None
            
            # --- Parsing ---
            metadata = self.parse_json_ld(html)
            if not metadata or not metadata.get('title'):
                fallback = self.extract_fallback_metadata(html, url)
                metadata = {**fallback, **(metadata or {})}

            if not metadata or not metadata.get('title'):
                logger.warning(f"Skipping article without title: {url}")
                return None

            article = {
                'url': url,
                'title': metadata.get('title', '').strip(),
                'description': metadata.get('description', '').strip(),
                'image': metadata.get('image', ''),
                'author': metadata.get('author', '').strip(),
                'date_published': normalize_date(metadata.get('date_published')),
                'date_modified': normalize_date(metadata.get('date_modified')),
                'fetched_at': datetime.utcnow(),
                'source': source, 'section': section, 'site': self.get_site_domain()
            }
            return article
        except Exception as e:
            logger.error(f"Error parsing article {url}: {e}", exc_info=True)
            return None

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        logger.info("OleScraper does not support pagination.")
        return None