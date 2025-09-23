import os
import logging
import json
import asyncio
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template, Response, g
from .scraper import LanceScraper
from .feeds import FeedGenerator
from . import store as store_module
from .scheduler import FeedScheduler
from .utils import validate_admin_key, parse_query_filter
from .sources_config import SOURCES_CONFIG as SOURCES
from .scraper_factory import ScraperFactory

class JsonFormatter(logging.Formatter):
    """Formats log records as a JSON string for NDJSON."""
    def format(self, record):
        log_object = {
            'ts': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.name,
        }
        
        # Add extra attributes passed to the logger if they exist
        extra_keys = ['httpCode', 'feed', 'url', 'source', 'section']
        for key in extra_keys:
            if hasattr(record, key):
                log_object[key] = getattr(record, key)

        return json.dumps(log_object, ensure_ascii=False)

# Generate a timestamp for this server run to create a unique log file
run_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')

# Create a logs directory if it doesn't exist
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logging
log_file_path = os.path.join(log_dir, f'app-{run_timestamp}.log.ndjson')
file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
file_handler.setFormatter(JsonFormatter())

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        file_handler
    ]
)
# Suppress DEBUG logs from urllib3.connectionpool
logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
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
ADMIN_KEY = os.environ.get("ADMIN_KEY") # Can be None
if not ADMIN_KEY:
    logger.warning("ADMIN_KEY environment variable not set. Admin endpoints will be inaccessible.")

# Initialize components
store = store_module.ArticleStore()

scraper = LanceScraper(store, request_delay=REQUEST_DELAY_MS/1000.0)
feed_generator = FeedGenerator()
scheduler = FeedScheduler(scraper, store, refresh_interval_minutes=5)

# Start background scheduler
scheduler.start()

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = store.get_conn()
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/')
def index():
    """Landing page with feed information and usage examples"""
    feeds_with_stats = store_module.get_all_feeds_with_stats(get_db())
    return render_template('index.html', feeds=feeds_with_stats, SOURCES_CONFIG=SOURCES)

@app.route('/logs')
def logs_viewer():
    """Serves the log viewer page."""
    # This route simply renders the static HTML page for the log viewer.
    return render_template('logs.html')

@app.route('/api/logs')
def get_server_logs():
    """Returns the content of the server's NDJSON log file."""
    filename = request.args.get('file')
    if not filename:
        return jsonify({'error': 'Nome do arquivo de log não especificado.'}), 400

    # Security: Prevent directory traversal attacks. Only allow simple filenames.
    safe_filename = os.path.basename(filename)
    if safe_filename != filename or not safe_filename.endswith('.ndjson'):
        return jsonify({'error': 'Nome de arquivo inválido.'}), 400

    try:
        log_file_path = os.path.join('logs', safe_filename)
        if not os.path.exists(log_file_path):
            return jsonify({'error': f'Arquivo de log "{safe_filename}" não encontrado.'}), 404
            
        with open(log_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return Response(content, mimetype='application/x-ndjson')
    except Exception as e:
        logger.error(f"Error reading log file: {e}", extra={'error_details': str(e)})
        return jsonify({'error': 'Failed to read log file'}), 500

@app.route('/api/logs/list')
def list_server_logs():
    """Lists all available NDJSON log files."""
    try:
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            return jsonify([])

        log_files = [f for f in os.listdir(log_dir) if f.endswith('.ndjson')]
        log_files.sort(reverse=True) # Show newest first
        return jsonify(log_files)
    except Exception as e:
        logger.error(f"Error listing log files: {e}")
        return jsonify({'error': 'Failed to list log files'}), 500

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
        articles = store_module.get_recent_articles(
            conn=get_db(),
            limit=limit, 
            query_filter=query_filter,
            source=source,
            section=section,
            exclude_authors=exclude_authors
        )
        
        # Decide if a refresh is needed
        should_refresh = False
        if force_refresh:
            should_refresh = True
            logger.info(f"Force refresh requested for {source}/{section}")
        elif not articles:
            should_refresh = True
            logger.info(f"No articles found for {source}/{section}, triggering refresh.")
        else:
            # Refresh if data is older than 5 minutes
            last_update = store_module.get_last_update_for_section(get_db(), source, section)
            if not last_update or (datetime.now(timezone.utc) - last_update) > timedelta(minutes=5):
                should_refresh = True
                logger.info(f"Feed for {source}/{section} is stale (last update: {last_update}), triggering refresh.")
        
        if should_refresh:
            # Use ScraperFactory to scrape any source
            # This now returns a tuple: (new_articles, links_found)
            new_articles, links_found = ScraperFactory.scrape_source_section(
                source=source, 
                section=section, 
                store=store, 
                max_pages=2,  # Reduced for performance
                max_articles=20,  # Limit articles to prevent timeouts
                request_delay=0.3  # Reduced delay for faster scraping
            )
            added_count = len(new_articles)
            logger.info(f"Scraped {added_count} new articles for {source}/{section}")
            # Update stats in the database
            store_module.update_feed_stats(get_db(), source, section, links_found, added_count)

            articles = store_module.get_recent_articles(
                conn=get_db(),
                limit=limit,
                query_filter=query_filter,
                source=source,
                section=section,
                exclude_authors=exclude_authors
            )

        # Add a final validation layer for Olé before generating the feed, as a safeguard.
        if source == 'ole':
            from .ole_scraper import _is_valid_ole_article_url
            original_count = len(articles)
            articles = [a for a in articles if _is_valid_ole_article_url(a['url'])]
            filtered_count = original_count - len(articles)
            if filtered_count > 0:
                logger.info(f"Final filter removed {filtered_count} invalid Olé articles before feed generation.")
        elif source == 'abola':
            from .abola_scraper import _is_valid_abola_article_url
            original_count = len(articles)
            articles = [a for a in articles if _is_valid_abola_article_url(a['url'])]
            filtered_count = original_count - len(articles)
            if filtered_count > 0:
                logger.info(f"Final filter removed {filtered_count} invalid A Bola articles before feed generation.")
        
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
        articles = store_module.get_recent_articles(conn=get_db(), limit=limit, query_filter=query_filter, source='lance')

        # If no recent articles or forced refresh, scrape new content
        if not articles or request.args.get('refresh') == '1':
            logger.info("Triggering fresh scrape for RSS feed")
            new_articles = scraper.scrape_and_store(source_url, max_pages=pages)
            articles = store_module.get_recent_articles(conn=get_db(), limit=limit, query_filter=query_filter, source='lance')

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
        articles = store_module.get_recent_articles(conn=get_db(), limit=limit, query_filter=query_filter, source='lance')

        # If no recent articles or forced refresh, scrape new content
        if not articles or request.args.get('refresh') == '1':
            logger.info("Triggering fresh scrape for Atom feed")
            new_articles = scraper.scrape_and_store(source_url, max_pages=pages)
            articles = store_module.get_recent_articles(conn=get_db(), limit=limit, query_filter=query_filter, source='lance')

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
        stats = store_module.get_stats(get_db())
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
    if not ADMIN_KEY:
        return jsonify({'error': 'Acesso negado: A chave de administrador (ADMIN_KEY) não foi configurada no servidor.'}), 403

    # Validate admin key
    provided_key = request.args.get('key', '')
    if not validate_admin_key(provided_key, ADMIN_KEY): # type: ignore
        return jsonify({'error': 'Chave de administrador inválida.'}), 401
    try:

        # Parse parameters
        pages = min(int(request.args.get('pages', MAX_PAGES)), 10)
        # Fixed source URL for security
        source_url = 'https://www.lance.com.br/mais-noticias'

        logger.info(f"Manual refresh triggered: pages={pages}")

        # Perform scraping
        new_articles = scraper.scrape_and_store(source_url, max_pages=pages)
        stats = store_module.get_stats(get_db())

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
    if not ADMIN_KEY:
        return jsonify({'error': 'Acesso negado: A chave de administrador (ADMIN_KEY) não foi configurada no servidor.'}), 403
    
    provided_key = request.args.get('key', '')
    if not validate_admin_key(provided_key, ADMIN_KEY): # type: ignore
        return jsonify({'error': 'Chave de administrador inválida.'}), 401
    try:

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