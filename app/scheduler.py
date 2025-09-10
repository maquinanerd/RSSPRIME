import logging
import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

class FeedScheduler:
    def __init__(self, scraper, store, refresh_interval_minutes=10):
        self.scraper = scraper
        self.store = store
        self.refresh_interval_minutes = refresh_interval_minutes
        self.scheduler = BackgroundScheduler()
        self.is_running_flag = False
        self.last_run = None
        self.lock = threading.Lock()
    
    def start(self):
        """Start the background scheduler"""
        try:
            # Add the refresh job
            self.scheduler.add_job(
                func=self._refresh_job,
                trigger=IntervalTrigger(minutes=self.refresh_interval_minutes),
                id='feed_refresh',
                name='Feed Refresh Job',
                replace_existing=True,
                max_instances=1  # Prevent overlapping runs
            )
            
            self.scheduler.start()
            logger.info(f"Scheduler started - refresh every {self.refresh_interval_minutes} minutes")
            
            # Run initial refresh in background
            self.scheduler.add_job(
                func=self._initial_refresh,
                trigger='date',
                run_date=datetime.now(),
                id='initial_refresh',
                name='Initial Refresh',
                max_instances=1
            )
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
    
    def stop(self):
        """Stop the background scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    def is_running(self):
        """Check if scheduler is running"""
        return self.scheduler.running if self.scheduler else False
    
    def _initial_refresh(self):
        """Initial refresh on startup"""
        try:
            # Check if we have any articles in the database
            stats = self.store.get_stats()
            
            if stats['total_articles'] == 0:
                logger.info("No articles in database, performing initial scrape")
                self._refresh_job()
            else:
                logger.info(f"Database has {stats['total_articles']} articles, skipping initial scrape")
                
        except Exception as e:
            logger.error(f"Error in initial refresh: {e}")
    
    def _refresh_job(self):
        """Background job to refresh feeds"""
        with self.lock:
            if self.is_running_flag:
                logger.warning("Refresh job already running, skipping")
                return
            
            self.is_running_flag = True
        
        try:
            logger.info("Starting scheduled feed refresh")
            start_time = datetime.utcnow()
            
            # Perform scraping from multiple sources - mais páginas para pegar notícias mais recentes
            start_urls = [
                'https://www.lance.com.br/mais-noticias',
                'https://www.lance.com.br/brasileirao',
                'https://www.lance.com.br/futebol-nacional',
                'https://www.lance.com.br/futebol-internacional'
            ]
            new_articles = self.scraper.scrape_and_store(
                start_urls=start_urls,
                max_pages=5  # Aumentar para pegar mais notícias
            )
            
            # Update last run time
            self.last_run = datetime.utcnow()
            
            # Log results
            duration = (self.last_run - start_time).total_seconds()
            logger.info(f"Feed refresh completed in {duration:.1f}s - {len(new_articles)} new articles")
            
            # Optional: cleanup old articles (keep last 30 days)
            try:
                deleted_count = self.store.cleanup_old_articles(days_to_keep=30)
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old articles")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
                
        except Exception as e:
            logger.error(f"Error in refresh job: {e}")
        finally:
            with self.lock:
                self.is_running_flag = False
    
    def trigger_refresh(self):
        """Manually trigger a refresh (for admin endpoint)"""
        try:
            # Add a one-time job
            self.scheduler.add_job(
                func=self._refresh_job,
                trigger='date',
                run_date=datetime.now(),
                id=f'manual_refresh_{datetime.now().timestamp()}',
                name='Manual Refresh',
                max_instances=1
            )
            return True
        except Exception as e:
            logger.error(f"Error triggering manual refresh: {e}")
            return False
    
    def get_status(self):
        """Get scheduler status information"""
        return {
            'running': self.is_running(),
            'refresh_interval_minutes': self.refresh_interval_minutes,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'is_job_running': self.is_running_flag,
            'next_run': self._get_next_run_time()
        }
    
    def _get_next_run_time(self):
        """Get next scheduled run time"""
        try:
            job = self.scheduler.get_job('feed_refresh')
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except Exception:
            pass
        return None
