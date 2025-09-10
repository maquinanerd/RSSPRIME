import re
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

def get_user_agent():
    """Get a polite, identifiable User-Agent string"""
    return "Mozilla/5.0 (compatible; LanceFeedBot/1.0; +https://lance-feeds.repl.co/)"

def normalize_date(date_string):
    """Normalize various date formats to datetime object with UTC timezone"""
    if not date_string:
        return None
    
    try:
        if isinstance(date_string, datetime):
            # If already a datetime, ensure it has timezone info
            if date_string.tzinfo is None:
                return date_string.replace(tzinfo=timezone.utc)
            return date_string
        
        # Parse the date string
        parsed_date = date_parser.parse(date_string)
        
        # Ensure timezone info is present
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        
        return parsed_date
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse date '{date_string}': {e}")
        return None

def extract_mime_type(image_url):
    """Extract MIME type from image URL based on extension"""
    if not image_url:
        return 'image/jpeg'  # Default fallback
    
    # Extract file extension
    parsed_url = urlparse(image_url)
    path = parsed_url.path.lower()
    
    if path.endswith('.png'):
        return 'image/png'
    elif path.endswith('.jpg') or path.endswith('.jpeg'):
        return 'image/jpeg'
    elif path.endswith('.gif'):
        return 'image/gif'
    elif path.endswith('.webp'):
        return 'image/webp'
    elif path.endswith('.svg'):
        return 'image/svg+xml'
    else:
        return 'image/jpeg'  # Default fallback

def validate_admin_key(provided_key, expected_key):
    """Validate admin key for protected endpoints"""
    if not expected_key:
        return False  # No admin key configured
    
    return provided_key == expected_key

def parse_query_filter(query_string):
    """Parse and validate query filter string"""
    if not query_string:
        return None
    
    # Basic sanitization - remove potentially dangerous characters
    # Allow alphanumeric, spaces, and common punctuation
    sanitized = re.sub(r'[^\w\s\-\|\(\)]+', '', query_string)
    
    # Limit length to prevent abuse
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    return sanitized.strip()

def format_rfc2822_date(dt):
    """Format datetime for RSS (RFC 2822)"""
    if not dt:
        return None
    
    if isinstance(dt, str):
        dt = normalize_date(dt)
    
    if not dt:
        return None
    
    # Format as RFC 2822 (e.g., "Wed, 02 Oct 2024 15:00:00 +0000")
    return dt.strftime('%a, %d %b %Y %H:%M:%S +0000')

def format_iso8601_date(dt):
    """Format datetime for Atom (ISO 8601)"""
    if not dt:
        return None
    
    if isinstance(dt, str):
        dt = normalize_date(dt)
    
    if not dt:
        return None
    
    # Format as ISO 8601 (e.g., "2024-10-02T15:00:00Z")
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def sanitize_html(text):
    """Basic HTML sanitization for feed content"""
    if not text:
        return ""
    
    # Remove potentially dangerous HTML tags
    dangerous_tags = re.compile(r'<(script|style|iframe|object|embed)[^>]*>.*?</\1>', re.IGNORECASE | re.DOTALL)
    text = dangerous_tags.sub('', text)
    
    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    return text.strip()

def truncate_text(text, max_length=500):
    """Truncate text to specified length with ellipsis"""
    if not text or len(text) <= max_length:
        return text
    
    # Find last space before max_length to avoid cutting words
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # Only use space if it's not too far back
        truncated = truncated[:last_space]
    
    return truncated + '...'

def is_valid_url(url):
    """Check if URL is valid and from allowed domains"""
    try:
        parsed = urlparse(url)
        
        # Check if URL has scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Check if it's from lance.com.br
        if not parsed.netloc.endswith('lance.com.br'):
            return False
        
        return True
        
    except Exception:
        return False

def clean_text(text):
    """Clean text content for feed display"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common web artifacts
    text = re.sub(r'\n|\r|\t', ' ', text)
    
    # Trim and return
    return text.strip()
