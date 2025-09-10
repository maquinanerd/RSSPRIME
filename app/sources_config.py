"""
Configuration for multiple news sources and their sections
"""

SOURCES_CONFIG = {
    'lance': {
        'name': 'LANCE!',
        'base_url': 'https://www.lance.com.br',
        'language': 'pt-BR',
        'scraper_class': 'LanceScraper',
        'sections': {
            'futebol-nacional': {
                'name': 'Futebol Nacional',
                'start_urls': ['https://www.lance.com.br/futebol-nacional/mais-noticias'],
                'description': 'Notícias do futebol brasileiro',
                'filters': {}
            },
            'futebol-internacional': {
                'name': 'Futebol Internacional',
                'start_urls': ['https://www.lance.com.br/futebol-internacional/mais-noticias'],
                'description': 'Notícias do futebol internacional',
                'filters': {}
            },
            'libertadores': {
                'name': 'Libertadores',
                'start_urls': ['https://www.lance.com.br/libertadores/mais-noticias'],
                'description': 'Notícias da Copa Libertadores',
                'filters': {}
            },
            'copa-do-mundo': {
                'name': 'Copa do Mundo',
                'start_urls': ['https://www.lance.com.br/copa-do-mundo/mais-noticias'],
                'description': 'Notícias da Copa do Mundo',
                'filters': {}
            },
            'champions-league': {
                'name': 'Champions League',
                'start_urls': ['https://www.lance.com.br/champions-league/mais-noticias'],
                'description': 'Notícias da Liga dos Campeões',
                'filters': {}
            },
            'premier-league': {
                'name': 'Premier League',
                'start_urls': ['https://www.lance.com.br/premier-league/mais-noticias'],
                'description': 'Notícias da Premier League inglesa',
                'filters': {}
            },
            'la-liga': {
                'name': 'La Liga',
                'start_urls': ['https://www.lance.com.br/la-liga/mais-noticias'],
                'description': 'Notícias do Campeonato Espanhol',
                'filters': {}
            },
            'bundesliga': {
                'name': 'Bundesliga',
                'start_urls': ['https://www.lance.com.br/bundesliga/mais-noticias'],
                'description': 'Notícias do Campeonato Alemão',
                'filters': {}
            },
            'campeonato-italiano': {
                'name': 'Campeonato Italiano',
                'start_urls': ['https://www.lance.com.br/tudo-sobre/campeonato-italiano'],
                'description': 'Notícias da Serie A italiana',
                'filters': {}
            },
            'ligue-1': {
                'name': 'Ligue 1',
                'start_urls': ['https://www.lance.com.br/ligue-1/mais-noticias'],
                'description': 'Notícias do Campeonato Francês',
                'filters': {}
            },
            'futebol': {
                'name': 'Futebol Geral',
                'start_urls': ['https://www.lance.com.br/mais-noticias'],
                'description': 'Notícias gerais de futebol e esportes',
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