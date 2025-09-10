"""
Factory for creating scrapers for different news sources
"""

import logging
from .scraper import LanceScraper
from .uol_scraper import UolScraper  
from .folha_scraper import FolhaScraper
from .sources_config import SOURCES_CONFIG

logger = logging.getLogger(__name__)

class ScraperFactory:
    """Factory for creating appropriate scrapers based on source"""
    
    _scrapers = {}
    
    @classmethod
    def get_scraper(cls, source, store, request_delay=1.0):
        """Get or create a scraper for the specified source"""
        if source in cls._scrapers:
            return cls._scrapers[source]
        
        source_config = SOURCES_CONFIG.get(source)
        if not source_config:
            raise ValueError(f"Unknown source: {source}")
        
        scraper_class_name = source_config.get('scraper_class')
        if not scraper_class_name:
            raise ValueError(f"No scraper class defined for source: {source}")
        
        # Map scraper class names to actual classes
        scraper_classes = {
            'LanceScraper': LanceScraper,
            'UolScraper': UolScraper,
            'FolhaScraper': FolhaScraper
        }
        
        scraper_class = scraper_classes.get(scraper_class_name)
        if not scraper_class:
            raise ValueError(f"Unknown scraper class: {scraper_class_name}")
        
        # Create and cache scraper instance
        scraper = scraper_class(store, request_delay=request_delay)
        cls._scrapers[source] = scraper
        
        logger.info(f"Created {scraper_class_name} for source '{source}'")
        return scraper
    
    @classmethod
    def get_all_scrapers(cls, store, request_delay=1.0):
        """Get scrapers for all configured sources"""
        scrapers = {}
        for source in SOURCES_CONFIG.keys():
            try:
                scrapers[source] = cls.get_scraper(source, store, request_delay)
            except Exception as e:
                logger.error(f"Failed to create scraper for {source}: {e}")
        return scrapers
    
    @classmethod
    def clear_cache(cls):
        """Clear cached scrapers (useful for testing)"""
        cls._scrapers.clear()
    
    @classmethod
    def scrape_source_section(cls, source, section, store, max_pages=3, request_delay=1.0):
        """Scrape a specific source and section"""
        try:
            scraper = cls.get_scraper(source, store, request_delay)
            source_config = SOURCES_CONFIG[source]
            section_config = source_config['sections'][section]
            
            start_urls = section_config.get('start_urls', [])
            if not start_urls:
                logger.warning(f"No start URLs configured for {source}/{section}")
                return []
            
            # For now, scrape the first URL
            # TODO: Implement multi-URL scraping
            url = start_urls[0]
            
            logger.info(f"Scraping {source}/{section} from {url}")
            return scraper.scrape_and_store(url, max_pages=max_pages, source=source, section=section)
            
        except Exception as e:
            logger.error(f"Failed to scrape {source}/{section}: {e}")
            return []