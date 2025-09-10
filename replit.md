# Overview

This is a web application that generates unofficial RSS and Atom feeds for LANCE! sports news portal. The project demonstrates responsible web scraping techniques by parsing article listings, extracting metadata using JSON-LD structured data, and generating standardized RSS/Atom feeds. It includes a Flask web server with automatic background scheduling, SQLite-based article storage with deduplication, and a web dashboard for monitoring feed statistics.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework
- **Flask-based web server** - Provides HTTP endpoints for feed generation and admin functionality
- **Template rendering** - Uses Jinja2 templates with Bootstrap dark theme for the web interface
- **Static file serving** - Serves CSS and other static assets

## Web Scraping System
- **Responsible scraping approach** - Respects robots.txt, implements request delays, and uses proper User-Agent headers
- **Multi-stage extraction process** - First scrapes article listing pages, then fetches individual articles for metadata
- **JSON-LD metadata extraction** - Parses structured data from article pages to get accurate titles, descriptions, dates, and images
- **Pagination handling** - Follows canonical pagination links starting from `/mais-noticias` endpoint
- **Retry mechanism** - Uses tenacity library for robust HTTP request handling with exponential backoff

## Data Storage
- **SQLite database** - Stores articles with deduplication based on URL primary key
- **Article schema** - Tracks URL, title, description, image, author, publication dates, and fetch timestamps
- **Performance optimization** - Uses database indexes on date fields for efficient querying
- **Data persistence** - Creates data directory structure automatically

## Feed Generation
- **Dual format support** - Generates both RSS 2.0 and Atom 1.0 feeds using feedgen library
- **Rich metadata** - Includes article images as enclosures with proper MIME type detection
- **Feed customization** - Supports query parameters for limiting results, filtering by search terms, and forcing refreshes
- **Standard compliance** - Follows RSS and Atom specifications with proper namespaces and required fields

## Background Processing
- **Automatic scheduling** - Uses APScheduler to refresh feeds every 15 minutes
- **Concurrent safety** - Implements threading locks and max instances to prevent overlapping runs
- **Manual refresh capability** - Provides admin endpoint for on-demand feed updates
- **Initial data loading** - Performs startup refresh to populate feeds immediately

## API Design
- **RESTful endpoints** - Clean URL structure for feeds and utility functions
- **Query parameter support** - Flexible filtering and pagination options
- **Health monitoring** - Status endpoint with system metrics and statistics
- **Admin functionality** - Protected refresh endpoint with key-based authentication

# External Dependencies

## Core Web Framework
- **Flask** - Main web application framework for handling HTTP requests and responses
- **Jinja2** - Template engine for rendering HTML pages (included with Flask)

## Web Scraping and HTTP
- **requests** - HTTP client library for fetching web pages and handling sessions
- **BeautifulSoup4** - HTML parsing library for extracting links and content from web pages
- **tenacity** - Retry library for robust HTTP request handling with exponential backoff

## Feed Generation
- **feedgen** - Library for generating RSS and Atom feeds with proper XML formatting
- **python-dateutil** - Advanced date parsing library for handling various date formats

## Background Processing
- **APScheduler** - Advanced Python Scheduler for background feed refresh jobs

## Data Storage
- **sqlite3** - Built-in Python SQLite database interface (no external dependency)

## Utility Libraries
- **urllib.robotparser** - Built-in Python library for parsing and respecting robots.txt files
- **pathlib** - Built-in Python library for file system path operations

## Frontend Assets (CDN)
- **Bootstrap** - CSS framework served from Replit CDN for responsive UI design
- **Font Awesome** - Icon library served from CDN for visual elements

## Environment and Configuration
- **os** - Built-in Python library for environment variable access
- **logging** - Built-in Python logging framework for application monitoring