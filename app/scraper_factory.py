"""
Factory for creating scrapers for different news sources.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Type, Any, Tuple

# --- Scrapers locais ---
from . import store as store_module
from .lance_scraper import LanceScraper
from .uol_scraper import UolScraper
from .folha_scraper import FolhaScraper
from .gazeta_scraper import GazetaScraper
from .globo_scraper import GloboScraper
from .g1_scraper import G1Scraper

# --- Scrapers internacionais / extras ---
from .as_scraper import ASScraper
from .ole_scraper import OleScraper
from .marca_scraper import MarcaScraper
from .theguardian_scraper import TheGuardianScraper
from .lequipe_scraper import LEquipeScraper
from .kicker_scraper import KickerScraper
from .gazzetta_scraper import GazzettaScraper
from .abola_scraper import ABolaScraper
from .foxsports_scraper import FoxSportsScraper
from .cbssports_scraper import CBSSportsScraper

from .sources_config import SOURCES_CONFIG
from .scheduler_locks import acquire_lock, release_lock

logger = logging.getLogger(__name__)


class ScraperFactory:
    """Factory para criar scrapers apropriados com base no 'source'."""

    # cache de instâncias por fonte
    _scrapers: Dict[str, Any] = {}

    # mapa estático de nomes -> classes
    SCRAPER_CLASSES: Dict[str, Type[Any]] = {
        # BR / locais
        "LanceScraper": LanceScraper,
        "UolScraper": UolScraper,
        "FolhaScraper": FolhaScraper,
        "GazetaScraper": GazetaScraper,
        "GloboScraper": GloboScraper,
        "G1Scraper": G1Scraper,
        # Internacionais / extras
        "ASScraper": ASScraper,
        "OleScraper": OleScraper,
        "MarcaScraper": MarcaScraper,
        "TheGuardianScraper": TheGuardianScraper,
        "LEquipeScraper": LEquipeScraper,
        "KickerScraper": KickerScraper,
        "GazzettaScraper": GazzettaScraper,
        "ABolaScraper": ABolaScraper,
        "FoxSportsScraper": FoxSportsScraper,
        "CBSSportsScraper": CBSSportsScraper,
    }

    @classmethod
    def get_scraper(cls, source: str, store: Any, request_delay: float = 1.0) -> Any:
        """
        Retorna (ou cria) o scraper para a fonte informada.

        Se já existir em cache, reutiliza. Garante que o .store e o delay
        sejam atualizados na instância (caso tenham mudado).
        """
        source_config = SOURCES_CONFIG.get(source)
        if not source_config:
            raise ValueError(f"Unknown source: {source}")

        scraper_class_name = source_config.get("scraper_class")
        if not scraper_class_name:
            raise ValueError(f"No scraper class defined for source: {source}")

        scraper_class = cls.SCRAPER_CLASSES.get(scraper_class_name)
        if not scraper_class:
            raise ValueError(f"Unknown scraper class: {scraper_class_name}")

        if source in cls._scrapers:
            scraper = cls._scrapers[source]
            # atualiza referências se necessário
            if hasattr(scraper, "store"):
                scraper.store = store
            if hasattr(scraper, "request_delay"):
                scraper.request_delay = request_delay
            return scraper

        # cria e cacheia
        scraper = scraper_class(store, request_delay=request_delay)
        cls._scrapers[source] = scraper
        logger.info(f"Created {scraper_class_name} for source '{source}'")
        return scraper

    @classmethod
    def get_all_scrapers(cls, store: Any, request_delay: float = 1.0) -> Dict[str, Any]:
        """Cria/retorna scrapers para todas as fontes configuradas em SOURCES_CONFIG."""
        scrapers: Dict[str, Any] = {}
        for source in SOURCES_CONFIG.keys():
            try:
                scrapers[source] = cls.get_scraper(source, store, request_delay)
            except Exception as e:
                logger.error(f"Failed to create scraper for {source}: {e}")
        return scrapers

    @classmethod
    def clear_cache(cls) -> None:
        """Limpa o cache de scrapers (útil em testes)."""
        cls._scrapers.clear()

    @classmethod
    def scrape_source_section(
        cls,
        source: str,
        section: str,
        store: Any,
        max_pages: int = 2,
        max_articles: int = 20,
        request_delay: float = 0.3,
    ) -> Tuple[List[dict], int]:
        """
        Faz o scraping de uma fonte/seção específica com limites de performance.

        - Respeita start_urls da seção.
        - Deduplica URLs.
        - Limita quantidade de artigos.
        - Aplica filtros definidos em SOURCES_CONFIG.

        Returns:
            A tuple containing:
            - A list of newly scraped article dictionaries.
            - The total number of unique article links found.
        """
        lock_key = (source, section)
        if not acquire_lock(lock_key):
            logger.info(f"Refresh for {source}/{section} is already in progress, skipping.")
            return [], 0

        try:
            scraper = cls.get_scraper(source, store, request_delay)
            source_config = SOURCES_CONFIG.get(source)
            if not source_config:
                logger.error(f"Source '{source}' not found in SOURCES_CONFIG.")
                return [], 0

            sections = source_config.get("sections", {})
            if section not in sections:
                logger.error(f"Section '{section}' not configured for source '{source}'.")
                return []

            section_config = sections[section]
            
            # Prioriza o feed RSS oficial, se disponível.
            official_rss_url = section_config.get("official_rss")
            if official_rss_url:
                start_urls = [official_rss_url]
            else:
                start_urls = section_config.get("start_urls", [])

            if not start_urls:
                logger.warning(f"Nenhuma URL de início (start_urls ou official_rss) configurada para {source}/{section}")
                return [], 0

            filters = section_config.get("filters", {}) or {}

            # Coleta URLs de artigos de todas as start_urls (com deduplicação)
            all_article_urls: List[str] = []
            for start_url in start_urls:
                logger.info(
                    f"Listing pages for {source}/{section} from {start_url} (max_pages={max_pages})"
                )
                try:
                    urls = scraper.list_pages(start_url, max_pages, section=section) or []
                    all_article_urls.extend(urls)
                except Exception as e:
                    logger.error(f"Failed listing pages from {start_url}: {e}")

            # Deduplica mantendo ordem
            seen = set()
            deduped_urls = []
            for u in all_article_urls:
                if u not in seen:
                    seen.add(u)
                    deduped_urls.append(u)

            total_links_found = len(deduped_urls)

            # Limita quantidade
            limited_urls = deduped_urls[:max_articles]
            logger.info(
                f"Scraping {source}/{section}: processing {len(limited_urls)} "
                f"articles (found {total_links_found})"
            )

            new_articles: List[dict] = []
            conn = store.get_conn()
            try:
                for i, article_url in enumerate(limited_urls, 1):
                    try:
                        logger.info(f"[{i}/{len(limited_urls)}] Parsing: {article_url}")

                        # Check if article already exists in the store to prevent re-parsing
                        if store_module.has_article(conn, article_url):
                            logger.debug(f"Article already exists in store, skipping parsing: {article_url}")
                            continue
                        article = scraper.parse_article(article_url, source=source, section=section)
                        if not article:
                            continue

                        # Filtros (se o método retornar True = filtrar/descartar)
                        if filters and getattr(scraper, "apply_filters", None):
                            if scraper.apply_filters(article, filters):
                                logger.info(f"Article filtered out: {article_url}")
                                continue

                        # Upsert no store
                        if store_module.upsert_article(conn, article):
                            new_articles.append(article)
                            logger.info(f"Stored: {article.get('title')}")

                        if i < len(limited_urls) and request_delay > 0:
                            time.sleep(request_delay)

                    except Exception as e:
                        logger.error(f"Error processing article {article_url}: {e}", exc_info=True)
                        continue
            finally:
                conn.close()

            return new_articles, total_links_found

        except Exception as e:
            logger.error(f"Failed to scrape {source}/{section}: {e}", exc_info=True)
            return [], 0
        finally:
            release_lock(lock_key)
# --- Fim do arquivo scraper_factory.py ---