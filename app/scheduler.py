import logging
import threading
import time
import json
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from . import store as store_module
from . import feed_processor
from .sources_config import SOURCES_CONFIG
from .scraper_factory import ScraperFactory

logger = logging.getLogger(__name__)

# Definition of topics, their sources, and processing rules as per the prompt
TOPIC_DEFINITIONS = {
    "esportes_nacionais": {
        "priority_source_order": ["ge", "lance"],
        "sources": {
            "ge": ["futebol"],
            "lance": ["futebol"]
        }
    },
    "economia_politica": {
        "priority_source_order": ["g1", "folha"], # valor and estadao not in SOURCES_CONFIG
        "sources": {
            "g1": ["economia", "politica"],
            "folha": ["economia", "politica"]
        }
    },
    "internacional_latam": {
        "priority_source_order": ["ole", "as_cl", "as_co", "as_mx"],
        "sources": {
            "ole": ["primera", "ascenso"],
            "as_cl": ["futbol"],
            "as_co": ["futbol"],
            "as_mx": ["futbol"]
        }
    },
    "internacional_europa": {
        "priority_source_order": ["as_es", "marca", "theguardian", "lequipe", "kicker", "gazzetta", "abola"],
        "sources": {
            "as_es": ["primera", "copa_del_rey", "segunda"],
            "marca": ["futbol"],
            "theguardian": ["football"],
            "lequipe": ["football"],
            "kicker": ["bundesliga", "2-bundesliga"],
            "gazzetta": ["calcio"],
            "abola": ["ultimas"]
        }
    },
    "ligas_eua": {
        "priority_source_order": ["foxsports", "cbssports"],
        "sources": {
            "foxsports": ["nfl", "college-football", "mlb", "nba"],
            "cbssports": ["nfl", "college-football", "mlb", "nba"]
        }
    }
}

class FeedScheduler:
    def __init__(self, store, refresh_interval_minutes=30):
        self.store = store
        self.refresh_interval_minutes = refresh_interval_minutes
        self.scheduler = BackgroundScheduler()
        self.is_running_flag = False
        self.last_run = None
        self.lock = threading.Lock()

    def start(self):
        """Start the background scheduler"""
        try:
            self.scheduler.add_job(
                func=self._refresh_job,
                trigger=IntervalTrigger(minutes=self.refresh_interval_minutes),
                id='feed_refresh',
                name='Feed Aggregation Job',
                replace_existing=True,
                max_instances=1
            )
            self.scheduler.start()
            logger.info(f"Scheduler started - refresh every {self.refresh_interval_minutes} minutes")

            self.scheduler.add_job(
                func=self._initial_refresh,
                trigger='date',
                run_date=datetime.now(timezone.utc),
                id='initial_refresh',
                name='Initial Refresh'
            )
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")

    def stop(self):
        """Stop the background scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def is_running(self):
        return self.scheduler.running if self.scheduler else False

    def _initial_refresh(self):
        """Initial refresh on startup to ensure there is data."""
        logger.info("Performing initial data aggregation.")
        self._refresh_job()

    def _refresh_job(self):
        """Background job to scrape, process, and store feeds for all topics."""
        with self.lock:
            if self.is_running_flag:
                logger.warning("Aggregation job already running, skipping.")
                return
            self.is_running_flag = True

        logger.info("Starting feed aggregation for all topics.")
        start_time = datetime.now(timezone.utc)

        try:
            for topic, definition in TOPIC_DEFINITIONS.items():
                logger.info(f"Processing topic: {topic}")
                
                input_data_for_processor = {
                    "run_id": f"run_{datetime.now(timezone.utc).timestamp()}",
                    "topic": topic,
                    "priority_source_order": definition["priority_source_order"],
                    "feeds": [],
                    "max_items": 200
                }

                for source, sections in definition["sources"].items():
                    source_items = []
                    for section in sections:
                        try:
                            logger.info(f"Scraping {source}/{section} for topic {topic}")
                            # We no longer save to store here, just get the articles
                            new_articles, _ = ScraperFactory.scrape_source_section(
                                source, section, self.store, 
                                max_pages=1, max_articles=20, request_delay=0.5, save_to_db=False
                            )
                            source_items.extend(new_articles)
                            time.sleep(1) # Be nice to servers
                        except Exception as e:
                            logger.error(f"Error scraping {source}/{section}: {e}")
                            continue
                    
                    if source_items:
                        # The processor expects a specific format for items
                        formatted_items = []
                        for item in source_items:
                            formatted_items.append({
                                "title": item.get('title'),
                                "link": item.get('url'),
                                "pubDate": item.get('date_published', datetime.now(timezone.utc)).isoformat(),
                                "summary": item.get('description'),
                                "categories": item.get('tags', []),
                                "lang": SOURCES_CONFIG.get(source, {}).get('language'),
                                "image": item.get('image')
                            })

                        input_data_for_processor["feeds"].append({
                            "source": source,
                            "category": topic, # Or derive from section if needed
                            "items": formatted_items
                        })

                # Process the collected data for the topic
                processed_data = feed_processor.process_feed_data(input_data_for_processor)

                # Save the final processed JSON to the database
                conn = self.store.get_conn()
                try:
                    store_module.save_processed_topic(
                        conn,
                        topic,
                        json.dumps(processed_data, indent=2),
                        processed_data['updated_at']
                    )
                finally:
                    conn.close()

            self.last_run = datetime.now(timezone.utc)
            duration = (self.last_run - start_time).total_seconds()
            logger.info(f"Feed aggregation completed in {duration:.1f}s")

        except Exception as e:
            logger.error(f"Fatal error in aggregation job: {e}", exc_info=True)
        finally:
            with self.lock:
                self.is_running_flag = False

    def trigger_refresh(self):
        """Manually trigger a refresh."""
        try:
            self.scheduler.add_job(
                func=self._refresh_job,
                trigger='date',
                run_date=datetime.now(timezone.utc),
                id=f'manual_refresh_{datetime.now().timestamp()}',
                name='Manual Refresh'
            )
            return True
        except Exception as e:
            logger.error(f"Error triggering manual refresh: {e}")
            return False

    def get_status(self):
        return {
            'running': self.is_running(),
            'refresh_interval_minutes': self.refresh_interval_minutes,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'is_job_running': self.is_running_flag,
            'next_run': self._get_next_run_time()
        }

    def _get_next_run_time(self):
        try:
            job = self.scheduler.get_job('feed_refresh')
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except Exception:
            pass
        return None
