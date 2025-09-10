"""
Configuration for multiple news sources and their sections
"""

SOURCES_CONFIG = {
    'gazeta': {
        'name': 'Gazeta Esportiva',
        'base_url': 'https://www.gazetaesportiva.com',
        'scraper_class': 'GazetaScraper',
        'language': 'pt-BR',
        'sections': {
            'todas-noticias': {
                'name': 'Todas as Notícias',
                'description': 'Todas as notícias da Gazeta Esportiva',
                'start_urls': ['https://www.gazetaesportiva.com/todas-as-noticias/'],
                'filters': {}
            },
            'futebol': {
                'name': 'Futebol',
                'description': 'Notícias de futebol da Gazeta Esportiva',
                'start_urls': ['https://www.gazetaesportiva.com/futebol/'],
                'filters': {}
            },
            'brasileirao': {
                'name': 'Brasileirão',
                'description': 'Notícias do Campeonato Brasileiro',
                'start_urls': ['https://www.gazetaesportiva.com/brasileirao/'],
                'filters': {}
            }
        }
    },
    'lance': {
        'name': 'LANCE!',
        'base_url': 'https://www.lance.com.br',
        'language': 'pt-BR',
        'scraper_class': 'LanceScraper',
        'sections': {
            'futebol': {
                'name': 'Futebol',
                'start_urls': [
                    'https://www.lance.com.br/mais-noticias',
                    'https://www.lance.com.br/brasileirao',
                    'https://www.lance.com.br/futebol-nacional',
                    'https://www.lance.com.br/futebol-internacional'
                ],
                'description': 'Notícias de futebol e esportes',
                'filters': {}
            }
        }
    },
    'uol': {
        'name': 'UOL',
        'base_url': 'https://www.uol.com.br',
        'language': 'pt-BR',
        'scraper_class': 'UolScraper',
        'sections': {
            'economia': {
                'name': 'Economia',
                'start_urls': ['https://www.uol.com.br/'],
                'description': 'Notícias de economia do UOL',
                'filters': {}
            },
            'politica': {
                'name': 'Política',
                'start_urls': ['https://noticias.uol.com.br/politica/'],
                'description': 'Notícias de política do UOL',
                'filters': {}
            },
            'mundo': {
                'name': 'Mundo',
                'start_urls': ['https://noticias.uol.com.br/internacional/'],
                'description': 'Notícias internacionais do UOL',
                'filters': {}
            },
            'futebol': {
                'name': 'Futebol',
                'start_urls': ['https://www.uol.com.br/esporte/futebol/ultimas/'],
                'description': 'Notícias de futebol do UOL',
                'filters': {
                    'exclude_authors': ['Gazeta Esportiva', 'gazeta-esportiva']
                }
            }
        }
    },
    'folha': {
        'name': 'Folha de S.Paulo',
        'base_url': 'https://www1.folha.uol.com.br',
        'language': 'pt-BR',
        'scraper_class': 'FolhaScraper',
        'sections': {
            'politica': {
                'name': 'Política',
                'start_urls': ['https://www1.folha.uol.com.br/poder/'],
                'description': 'Notícias de política da Folha',
                'filters': {}
            },
            'economia': {
                'name': 'Economia',
                'start_urls': ['https://www1.folha.uol.com.br/mercado/'],
                'description': 'Notícias de economia da Folha',
                'filters': {}
            },
            'mundo': {
                'name': 'Mundo',
                'start_urls': ['https://www1.folha.uol.com.br/mundo/'],
                'description': 'Notícias internacionais da Folha',
                'filters': {}
            }
        }
    }
}

# Alias for easier imports
SOURCES = SOURCES_CONFIG

def get_source_config(source):
    """Get configuration for a specific source"""
    return SOURCES_CONFIG.get(source)

def get_section_config(source, section):
    """Get configuration for a specific source section"""
    source_config = get_source_config(source)
    if not source_config:
        return None
    return source_config.get('sections', {}).get(section)

def get_all_sources():
    """Get list of all available sources"""
    return list(SOURCES_CONFIG.keys())

def get_source_sections(source):
    """Get list of all sections for a source"""
    source_config = get_source_config(source)
    if not source_config:
        return []
    return list(source_config.get('sections', {}).keys())

def validate_source_section(source, section):
    """Validate if source and section combination exists"""
    return get_section_config(source, section) is not None