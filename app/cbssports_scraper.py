import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class CBSSportsScraper(BaseScraper):
    """
    Scraper for CBS Sports (cbssports.com) news.
    """

    def __init__(self, store, request_delay=1.0):
        """Inicializa o scraper com cabeçalhos de navegador para evitar bloqueios."""
        super().__init__(store, request_delay)
        # Headers mais robustos para simular um navegador e evitar erros 406/403
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "cbssports.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extrai links de artigos da página de listagem do CBS Sports."""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Seletores atualizados para o layout moderno do CBS Sports.
        # Eles visam os contêineres de notícias e extraem o primeiro link.
        selectors = [
            'div.article-list-pack-item a[href]',
            'div.article-list-item-v2 a[href]',
            'article.article-list-item a[href]',
            'div[data-item-id] a[href]',
            'a.cell-inner[href]'
        ]

        for selector in selectors:
            # Itera sobre todos os links encontrados pelo seletor, não apenas o primeiro.
            for link_tag in soup.select(selector):
                href = link_tag['href']
                # Filter out non-article links
                if href and '/video/' not in href and '/live/' not in href:
                    full_url = urljoin(base_url, href.strip())
                    links.add(full_url)

        logger.info(f"Extraídos {len(links)} links de artigos únicos de {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        # CBS Sports often uses a "Load More" button driven by JavaScript.
        # A simple scraper can't easily follow this.
        logger.info(
            "CBSSportsScraper does not support pagination (likely JS-driven 'Load More' button)."
        )
        return None