import logging
import feedparser
from urllib.parse import urljoin, urlparse, urlunparse
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .utils import normalize_date

logger = logging.getLogger(__name__)

ABOLA_RSS = "https://www.abola.pt/rss-articles.xml"
BLACKLIST_SUBSTR = ("/video/", "/a-bola-tv/", "/programas/", "/videocasts/")

def _canonical(u: str) -> str:
    try:
        pu = urlparse(u)
        return urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
    except Exception:
        return u

def _is_valid_abola_article_url(url: str) -> bool:
    """Checks if a URL is a candidate for a valid A Bola news article."""
    if not url:
        return False

    path = urlparse(url).path.lower()
    # Article URLs typically contain news-related paths
    valid_paths = [
        "/noticia/", "/artigo/", "/futebol/", "/nacional/", "/internacional/",
        "/modalidades/", "/opiniao/", "/benfica/", "/sporting/", "/fc-porto/"
    ]
    if not any(p in path for p in valid_paths):
        return False

    if any(s in url for s in BLACKLIST_SUBSTR):
        return False
    return True

class ABolaScraper(BaseScraper):
    source = "abola"

    def __init__(self, store, request_delay=1.0):
        super().__init__(store, request_delay)
        self._rss_entries_by_link: dict = {}

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "abola.pt"

    def _extract_from_rss(self, section: str | None) -> list[str]:
        """
        Extracts article links from A Bola's official RSS feed and caches the entries.
        """
        self._rss_entries_by_link.clear()  # Clear cache for each run
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UnifiedFeedBot/1.0",
            "Accept": "application/rss+xml, application/atom+xml, */*",
            "Accept-Language": "pt-PT,pt-BR;q=0.9,en;q=0.8",
        }
        try:
            r = self.session.get(ABOLA_RSS, headers=headers, timeout=15)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)

            if parsed.bozo:
                logger.warning(f"Feedparser reported an error parsing A Bola RSS feed: {parsed.bozo_exception}")

            links: list[str] = []
            for e in parsed.entries:
                link = e.get("link") or e.get("id")
                if not link:
                    continue

                canonical_link = _canonical(link)
                if _is_valid_abola_article_url(canonical_link):
                    links.append(canonical_link)
                    self._rss_entries_by_link[canonical_link] = e  # Cache the full entry

            out: list[str] = []
            seen: set[str] = set()
            for u in links:
                if u not in seen:
                    seen.add(u)
                    out.append(u)

            if not out:
                logger.warning(f"[abola/{section}] No valid article links found in the RSS feed.")
            return out

        except Exception as e:
            logger.error(f"Failed to fetch or parse A Bola RSS feed: {e}", exc_info=True)
            return []

    def _parse_rss_entry(self, entry, source, section):
        """Parses a feedparser entry into a standard article dictionary."""
        link = entry.get("link", "").strip()
        title = entry.get("title", "").strip()

        # Use summary as the main description
        summary = entry.get("summary", "")

        # Image
        image_url = None
        if entry.get("media_content"):
            media_list = entry.get("media_content", [])
            if media_list and isinstance(media_list, list) and isinstance(media_list[0], dict):
                image_url = media_list[0].get("url")

        # Author
        authors = [a.get("name") for a in entry.get("authors", []) if a.get("name")]
        author_str = ", ".join(authors) if authors else ""

        # Dates
        pub_date = normalize_date(entry.get("published"))
        mod_date = normalize_date(entry.get("updated"))

        article = {
            'url': link,
            'title': title,
            'description': summary,
            'image': image_url,
            'author': author_str,
            'date_published': pub_date,
            'date_modified': mod_date,
            'fetched_at': datetime.now(timezone.utc),
            'source': source,
            'section': section,
            'site': self.get_site_domain()
        }
        return article

    def parse_article(self, url: str, source: str | None = None, section: str | None = None) -> dict | None:
        """
        Parses an article. If the URL came from the RSS feed (cached), it parses
        the feed entry directly. Otherwise, it falls back to the base scraper's
        HTML parsing.
        """
        if url in self._rss_entries_by_link:
            logger.debug(f"Parsing article from cached RSS entry: {url}")
            entry = self._rss_entries_by_link[url]
            return self._parse_rss_entry(entry, source, section)
        else:
            logger.warning(f"Article not in RSS cache, falling back to standard HTML parsing: {url}")
            return super().parse_article(url, source, section)

    def extract_article_links(self, html: str, base_url: str, section: str | None = None) -> list[str]:
        """
        Extracts article links from A Bola, trying RSS feed first, then falling
        back to HTML parsing with specific and generic selectors.
        """
        # 1. Attempt to get links from the official RSS feed first.
        # This will now also populate the self._rss_entries_by_link cache.
        rss_links = self._extract_from_rss(section)
        if rss_links:
            logger.info(f"[abola/{section}] Found {len(rss_links)} links via RSS feed.")
            return rss_links

        logger.warning(f"[abola/{section}] RSS feed was empty or failed. Falling back to HTML parsing of {base_url}.")

        if not html:
            logger.error(f"[abola/{section}] HTML content is missing, cannot perform HTML fallback.")
            return []

        soup = BeautifulSoup(html, 'lxml')
        links: set[str] = set()

        # 2. Fallback to specific CSS selectors for A Bola.
        for item in soup.select('div.media-body a[href]'):
            href = item.get('href')
            if href and href.startswith('/'):
                full_url = urljoin(base_url, href)
                if _is_valid_abola_article_url(full_url):
                    links.add(full_url)

        if links:
            logger.info(f"[abola/{section}] Found {len(links)} links via specific HTML selectors.")
            return list(links)

        logger.warning(f"[abola/{section}] Specific HTML selectors found no links. Falling back to generic discovery.")

        # 3. Final fallback: generic link discovery based on URL patterns.
        for a in soup.find_all("a", href=True):
            href = urljoin(base_url, a["href"].strip())
            if _is_valid_abola_article_url(href):
                links.add(_canonical(href))

        if links:
            logger.info(f"[abola/{section}] Found {len(links)} links via generic HTML discovery.")
            return list(links)

        logger.error(f"[abola/{section}] All extraction methods failed. No links found on {base_url}.")
        return []

    def find_next_page_url(self, html, current_url):
        """Pagination is not needed as we use the full RSS feed."""
        return None