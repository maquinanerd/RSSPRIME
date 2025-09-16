import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response
from .scraper import LanceScraper
from .feeds import FeedGenerator
from .store import ArticleStore
from .scheduler import FeedScheduler
from .utils import validate_admin_key, parse_query_filter
from .sources_config import SOURCES_CONFIG as SOURCES
from .scraper_factory import ScraperFactory

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    # For development only - use proper env var in production
    import secrets
    app.secret_key = secrets.token_hex(32)
    logger.warning("SESSION_SECRET not set, using temporary secret key for development")

# Configuration from environment
MAX_PAGES = int(os.environ.get("MAX_PAGES", "3"))
DEFAULT_LIMIT = int(os.environ.get("DEFAULT_LIMIT", "30"))
REQUEST_DELAY_MS = int(os.environ.get("REQUEST_DELAY_MS", "900"))
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")

# Initialize components
store = ArticleStore()
scraper = LanceScraper(store, request_delay=REQUEST_DELAY_MS/1000.0)
feed_generator = FeedGenerator()
scheduler = FeedScheduler(scraper, store)

# Start background scheduler
scheduler.start()

@app.route('/')
def index():
    """Landing page with feed information and usage examples"""
    try:
        stats = store.get_stats()
        return render_template('index.html', stats=stats)
    except Exception as e:
        logger.error(f"Error loading index page: {e}")
        return render_template('index.html', stats={'total_articles': 0, 'last_update': None})

@app.route('/feeds/<source>/<section>/<format>')
def dynamic_feeds(source, section, format):
    """Dynamic feeds for any source/section/format combination"""
    try:
        # Validate source and section
        if source not in SOURCES:
            return f"Unknown source: {source}", 404
        
        if section not in SOURCES[source]['sections']:
            return f"Unknown section '{section}' for source '{source}'", 404
        
        # Validate format
        if format not in ['rss', 'atom']:
            return f"Unsupported format: {format}. Use 'rss' or 'atom'", 400
        
        # Get parameters
        limit = min(int(request.args.get('limit', DEFAULT_LIMIT)), 100)
        query = request.args.get('q', '')
        force_refresh = request.args.get('refresh') == '1'
        
        # Get section-specific filters
        section_config = SOURCES[source]['sections'][section]
        exclude_authors = section_config.get('filters', {}).get('exclude_authors', [])
        
        # Get articles with filters
        query_filter = parse_query_filter(query) if query else None
        articles = store.get_recent_articles(
            limit=limit, 
            query_filter=query_filter,
            source=source,
            section=section,
            exclude_authors=exclude_authors
        )
        
        # Force refresh if requested and no recent articles
        if force_refresh or not articles:
            logger.info(f"Force refresh requested for {source}/{section}")
            # Use ScraperFactory to scrape any source
            new_articles = ScraperFactory.scrape_source_section(
                source=source, 
                section=section, 
                store=store, 
                max_pages=2,  # Reduced for performance
                max_articles=20,  # Limit articles to prevent timeouts
                request_delay=0.3  # Reduced delay for faster scraping
            )
            logger.info(f"Scraped {len(new_articles)} new articles for {source}/{section}")
            articles = store.get_recent_articles(
                limit=limit, 
                query_filter=query_filter,
                source=source,
                section=section,
                exclude_authors=exclude_authors
            )
        
        # Generate feed
        if format == 'rss':
            feed_content = feed_generator.generate_rss(articles, source=source, section=section)
            content_type = 'application/rss+xml'
        else:  # atom
            feed_content = feed_generator.generate_atom(articles, source=source, section=section)
            content_type = 'application/atom+xml'
        
        response = Response(feed_content, mimetype=content_type)
        response.headers['Cache-Control'] = 'public, max-age=900'  # 15 minutes cache
        return response
    
    except Exception as e:
        logger.error(f"Error generating {format} feed for {source}/{section}: {e}")
        return jsonify({'error': f'Failed to generate {format} feed'}), 500

# New routes for individual category feeds
@app.route('/feeds/lance/<section>/rss')
def lance_category_rss(section):
    """Generate RSS feed for specific LANCE! category"""
    try:
        # Validate section exists
        from .sources_config import validate_source_section
        if not validate_source_section('lance', section):
            return jsonify({'error': f'Unknown section: {section}'}), 404
        
        limit = min(int(request.args.get('limit', DEFAULT_LIMIT)), 100)
        force_refresh = request.args.get('refresh') == '1'
        
        logger.info(f"RSS feed requested for lance/{section}: limit={limit}, refresh={force_refresh}")
        
        # Get articles from database for this section
        articles = store.get_recent_articles(limit=limit, source='lance', section=section)
        
        # Force refresh if requested or no articles
        if force_refresh or not articles:
            logger.info(f"Force refresh requested for lance/{section}")
            new_articles = ScraperFactory.scrape_source_section(
                'lance', section, store, max_pages=2, max_articles=20, request_delay=0.3
            )
            logger.info(f"Scraped {len(new_articles)} new articles for lance/{section}")
            articles = store.get_recent_articles(limit=limit, source='lance', section=section)
        
        # Generate RSS feed
        rss_content = feed_generator.generate_rss(articles, source='lance', section=section)
        
        response = Response(rss_content, mimetype='application/rss+xml')
        response.headers['Cache-Control'] = 'public, max-age=900'
        return response
        
    except Exception as e:
        logger.error(f"Error generating RSS feed for lance/{section}: {e}")
        return jsonify({'error': f'Failed to generate RSS feed for {section}'}), 500

@app.route('/feeds/lance/<section>/atom')
def lance_category_atom(section):
    """Generate Atom feed for specific LANCE! category"""
    try:
        # Validate section exists
        from .sources_config import validate_source_section
        if not validate_source_section('lance', section):
            return jsonify({'error': f'Unknown section: {section}'}), 404
        
        limit = min(int(request.args.get('limit', DEFAULT_LIMIT)), 100)
        force_refresh = request.args.get('refresh') == '1'
        
        logger.info(f"Atom feed requested for lance/{section}: limit={limit}, refresh={force_refresh}")
        
        # Get articles from database for this section
        articles = store.get_recent_articles(limit=limit, source='lance', section=section)
        
        # Force refresh if requested or no articles
        if force_refresh or not articles:
            logger.info(f"Force refresh requested for lance/{section}")
            new_articles = ScraperFactory.scrape_source_section(
                'lance', section, store, max_pages=2, max_articles=20, request_delay=0.3
            )
            logger.info(f"Scraped {len(new_articles)} new articles for lance/{section}")
            articles = store.get_recent_articles(limit=limit, source='lance', section=section)
        
        # Generate Atom feed
        atom_content = feed_generator.generate_atom(articles, source='lance', section=section)
        
        response = Response(atom_content, mimetype='application/atom+xml')
        response.headers['Cache-Control'] = 'public, max-age=900'
        return response
        
    except Exception as e:
        logger.error(f"Error generating Atom feed for lance/{section}: {e}")
        return jsonify({'error': f'Failed to generate Atom feed for {section}'}), 500

# Legacy routes for backward compatibility
@app.route('/feeds/lance/rss.xml')
def rss_feed():
    """Generate RSS feed"""
    try:
        # Parse query parameters
        limit = min(int(request.args.get('limit', DEFAULT_LIMIT)), 100)
        pages = min(int(request.args.get('pages', MAX_PAGES)), 10)
        q = request.args.get('q', '')
        # Fixed source URL for security (no user-controlled URLs)
        source_url = 'https://www.lance.com.br/mais-noticias'

        logger.info(f"RSS feed requested: limit={limit}, pages={pages}, q='{q}'")

        # Get articles from database
        query_filter = parse_query_filter(q) if q else None
        articles = store.get_recent_articles(limit=limit, query_filter=query_filter)

        # If no recent articles or forced refresh, scrape new content
        if not articles or request.args.get('refresh') == '1':
            logger.info("Triggering fresh scrape for RSS feed")
            new_articles = scraper.scrape_and_store(source_url, max_pages=pages)
            articles = store.get_recent_articles(limit=limit, query_filter=query_filter)

        # Generate RSS feed
        rss_content = feed_generator.generate_rss(articles)

        response = Response(rss_content, mimetype='application/rss+xml')
        response.headers['Cache-Control'] = 'public, max-age=900'  # 15 minutes cache
        return response

    except Exception as e:
        logger.error(f"Error generating RSS feed: {e}")
        return jsonify({'error': 'Failed to generate RSS feed'}), 500

@app.route('/feeds/lance/atom.xml')
def atom_feed():
    """Generate Atom feed"""
    try:
        # Parse query parameters
        limit = min(int(request.args.get('limit', DEFAULT_LIMIT)), 100)
        pages = min(int(request.args.get('pages', MAX_PAGES)), 10)
        q = request.args.get('q', '')
        # Fixed source URL for security
        source_url = 'https://www.lance.com.br/mais-noticias'

        logger.info(f"Atom feed requested: limit={limit}, pages={pages}, q='{q}'")

        # Get articles from database
        query_filter = parse_query_filter(q) if q else None
        articles = store.get_recent_articles(limit=limit, query_filter=query_filter)

        # If no recent articles or forced refresh, scrape new content
        if not articles or request.args.get('refresh') == '1':
            logger.info("Triggering fresh scrape for Atom feed")
            new_articles = scraper.scrape_and_store(source_url, max_pages=pages)
            articles = store.get_recent_articles(limit=limit, query_filter=query_filter)

        # Generate Atom feed
        atom_content = feed_generator.generate_atom(articles)

        response = Response(atom_content, mimetype='application/atom+xml')
        response.headers['Cache-Control'] = 'public, max-age=900'  # 15 minutes cache
        return response

    except Exception as e:
        logger.error(f"Error generating Atom feed: {e}")
        return jsonify({'error': 'Failed to generate Atom feed'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint with metrics"""
    try:
        stats = store.get_stats()
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat(),
            'items': stats['total_articles'],
            'last_refresh': stats['last_update'],
            'scheduler_running': scheduler.is_running()
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/admin/refresh')
def admin_refresh():
    """Manual refresh endpoint (requires admin key)"""
    try:
        # Validate admin key
        provided_key = request.args.get('key', '')
        if not validate_admin_key(provided_key, ADMIN_KEY):
            return jsonify({'error': 'Invalid admin key'}), 401

        # Parse parameters
        pages = min(int(request.args.get('pages', MAX_PAGES)), 10)
        # Fixed source URL for security
        source_url = 'https://www.lance.com.br/mais-noticias'

        logger.info(f"Manual refresh triggered: pages={pages}")

        # Perform scraping
        new_articles = scraper.scrape_and_store(source_url, max_pages=pages)
        stats = store.get_stats()

        return jsonify({
            'status': 'success',
            'new_articles': len(new_articles),
            'total_articles': stats['total_articles'],
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Admin refresh error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/admin/stats')
def admin_stats():
    """Detailed statistics endpoint"""
    try:
        provided_key = request.args.get('key', '')
        if not validate_admin_key(provided_key, ADMIN_KEY):
            return jsonify({'error': 'Invalid admin key'}), 401

        detailed_stats = store.get_detailed_stats()
        return jsonify(detailed_stats)

    except Exception as e:
        logger.error(f"Admin stats error: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500