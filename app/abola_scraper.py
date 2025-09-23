import logging
import re
import feedparser
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Regex to match valid article URLs, e.g., /noticias/qualquer-coisa-123456789012
ARTICLE_ALLOW = re.compile(r"/noticias/.+-\d{12,}$", re.I)
# Regex to deny hub/section pages
DENY_PATTERNS = [
    r"/futebol/competicao/",
    r"/futebol/(benfica|sporting|fc-porto)-\d+",
    r"/futebol/resultados-em-direto",
    r"/modalidades", r"/videocasts", r"/a-bola-tv", r"/pesquisar",
]
DENY_RE = re.compile("|".join(DENY_PATTERNS), re.I)

def _is_valid_article(href: str) -> bool:
    """Checks if a URL is a valid, individual article page."""
    if not href:
        return False
    return bool(ARTICLE_ALLOW.search(href)) and not DENY_RE.search(href)

class ABolaScraper(BaseScraper):
    source = "abola"

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "abola.pt"

    def extract_article_links(self, html: str, base_url: str, section: str | None = None) -> list[str]:
        soup = BeautifulSoup(html, 'lxml')
        links: set[str] = set()

        # 1. Primary, specific selector for article titles
        anchors = soup.select('a[data-cy="article-title"]')

        # 2. Fallback to any link that looks like a news article URL
        if not anchors:
            logger.debug(f"[abola/{section}] Primary selector 'a[data-cy=\"article-title\"]' found no links. Trying fallback.")
            anchors = soup.select('a[href^="/noticias/"], a[href^="https://www.abola.pt/noticias/"]')

        total_found = len(anchors)
        allowed_count = 0

        for a in anchors:
            href = a.get("href")
            if not href:
                continue
            
            full_url = urljoin(base_url, href.strip())
            if _is_valid_article(full_url):
                links.add(full_url)
                allowed_count += 1
        
        denied_count = total_found - allowed_count
        final_count = len(links)
        logger.info(
            f"[abola/{section}] links from HTML: found={total_found}, allowed={allowed_count}, denied={denied_count}, after_dedup={final_count}"
        )

        return list(links)

    def find_next_page_url(self, html, current_url):
        # A Bola uses ?page=N for pagination
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
        
        parsed_url = urlparse(current_url)
        query_params = parse_qs(parsed_url.query)
        
        current_page = int(query_params.get('page', ['1'])[0])
        next_page = current_page + 1
        
        query_params['page'] = [str(next_page)]
        
        # Rebuild the URL with the new page number
        next_page_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            urlencode(query_params, doseq=True),
            parsed_url.fragment
        ))
        
        # The list_pages loop in BaseScraper will stop if a page is empty.
        logger.debug(f"Calculated next page for A Bola: {next_page_url}")
        return next_page_url

    def list_pages(self, start_url, max_pages=3, section=None):
        """
        Overrides BaseScraper.list_pages to add an RSS fallback.
        """
        # First, try the standard HTML scraping method
        html_links = super().list_pages(start_url, max_pages, section)
        if html_links:
            return html_links

        # If HTML scraping fails, fall back to the official RSS feed
        logger.warning(f"[abola/{section}] HTML scraping yielded no links. Trying RSS fallback.")
        try:
            from .sources_config import SOURCES_CONFIG
            rss_url = SOURCES_CONFIG.get('abola', {}).get('official_rss')
            if not rss_url:
                logger.error("[abola/ultimas] official_rss URL not configured.")
                return []

            logger.info(f"[abola/{section}] Fetching RSS fallback from {rss_url}")
            response = self.session.get(rss_url, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            rss_links = []
            for entry in feed.entries:
                link = entry.get("link")
                if _is_valid_article(link):
                    rss_links.append(link)
            
            logger.info(f"[abola/{section}] Found {len(rss_links)} valid links via RSS fallback.")
            return list(dict.fromkeys(rss_links)) # Deduplicate
        except Exception as e:
            logger.exception(f"[abola/{section}] RSS fallback failed: {e}")
            return []