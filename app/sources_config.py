                'filters': {}
            }
        }
    },
    # International Feeds
    'as_cl': {
        'name': 'AS Chile',
        'base_url': 'https://chile.as.com',
        'language': 'es-CL',
        'scraper_class': 'ASScraper',
        'sections': {
            'futbol': {
                'name': 'Fútbol',
                'description': 'Noticias de fútbol de Chile y del mundo.',
                'start_urls': ['https://chile.as.com/futbol/'],
                'filters': {}
            }
        }
    },
    'as_co': {
        'name': 'AS Colombia',
        'base_url': 'https://colombia.as.com',
        'language': 'es-CO',
        'scraper_class': 'ASScraper',
        'sections': {
            'futbol': {
                'name': 'Fútbol',
                'description': 'Noticias de fútbol de Colombia y del mundo.',
                'start_urls': ['https://colombia.as.com/futbol/'],
                'filters': {}
            }
        }
    },
    'as_mx': {
        'name': 'AS México',
        'base_url': 'https://mexico.as.com',
        'language': 'es-MX',
        'scraper_class': 'ASScraper',
        'sections': {
            'futbol': {
                'name': 'Fútbol',
                'description': 'Noticias de fútbol de México y del mundo.',
                'start_urls': ['https://mexico.as.com/futbol/'],
                'filters': {}
            }
        }
    },
    'ole': {
        'name': 'Olé',
        'base_url': 'https://www.ole.com.ar',
        'language': 'es-AR',
        'scraper_class': 'OleScraper',
        'sections': {
            'primera': {
                'name': 'Fútbol de Primera',
                'description': 'Noticias de la primera división del fútbol argentino.',
                'start_urls': ['https://www.ole.com.ar/futbol-primera'],
                'filters': {}
            },
            'ascenso': {
                'name': 'Fútbol de Ascenso',
                'description': 'Noticias del ascenso del fútbol argentino.',
                'start_urls': ['https://www.ole.com.ar/futbol-ascenso'],
                'filters': {}
            }
        }
    },
    'as_es': {
        'name': 'AS España',
        'base_url': 'https://as.com',
        'language': 'es-ES',
        'scraper_class': 'ASScraper',
        'sections': {
            'primera': {
                'name': 'LaLiga EA Sports',
                'description': 'Noticias de la primera división de España.',
                'start_urls': ['https://as.com/futbol/primera/'],
                'filters': {}
            },
            'copa_del_rey': {
                'name': 'Copa del Rey',
                'description': 'Noticias de la Copa del Rey.',
                'start_urls': ['https://as.com/futbol/copa_del_rey/'],
                'filters': {}
            },
            'segunda': {
                'name': 'LaLiga Hypermotion',
                'description': 'Noticias de la segunda división de España.',
                'start_urls': ['https://as.com/futbol/segunda/'],
                'filters': {}
            }
        }
    },
    'marca': {
        'name': 'Marca',
        'base_url': 'https://www.marca.com',
        'language': 'es-ES',
        'scraper_class': 'MarcaScraper',
        'sections': {
            'futbol': {
                'name': 'Fútbol',
                'description': 'Noticias de fútbol de Marca.',
                'start_urls': ['https://www.marca.com/futbol.html'],
                'filters': {}
            }
        }
    },
    'theguardian': {
        'name': 'The Guardian Football',
        'base_url': 'https://www.theguardian.com',
        'language': 'en-GB',
        'scraper_class': 'TheGuardianScraper',
        'sections': {
            'football': {
                'name': 'Football',
                'description': 'Football news, results, fixtures, blogs and comments.',
                'start_urls': ['https://www.theguardian.com/football'],
                'filters': {}
            }
        }
    },
    'lequipe': {
        'name': "L'Équipe",
        'base_url': 'https://www.lequipe.fr',
        'language': 'fr-FR',
        'scraper_class': 'LEquipeScraper',
        'sections': {
            'football': {
                'name': 'Football',
                'description': "L'actualité du football en direct.",
                'start_urls': ['https://www.lequipe.fr/Football/'],
                'filters': {}
            }
        }
    },
    'kicker': {
        'name': 'Kicker',
        'base_url': 'https://www.kicker.de',
        'language': 'de-DE',
        'scraper_class': 'KickerScraper',
        'sections': {
            'bundesliga': {
                'name': 'Bundesliga',
                'description': 'Aktuelle Nachrichten, Ergebnisse und Tabellen der Bundesliga.',
                'start_urls': ['https://www.kicker.de/bundesliga/startseite'],
                'filters': {}
            },
            '2-bundesliga': {
                'name': '2. Bundesliga',
                'description': 'Aktuelle Nachrichten, Ergebnisse und Tabellen der 2. Bundesliga.',
                'start_urls': ['https://www.kicker.de/2-bundesliga/startseite'],
                'filters': {}
            }
        }
    },
    'gazzetta': {
        'name': 'La Gazzetta dello Sport',
        'base_url': 'https://www.gazzetta.it',
        'language': 'it-IT',
        'scraper_class': 'GazzettaScraper',
        'sections': {
            'calcio': {
                'name': 'Calcio',
                'description': 'Notizie di calcio: scoop, risultati, classifiche.',
                'start_urls': ['https://www.gazzetta.it/Calcio/'],
                'filters': {}
            }
        }
    },
    'abola': {
        'name': 'A Bola',
        'base_url': 'https://www.abola.pt',
        'language': 'pt-PT',
        'scraper_class': 'ABolaScraper',
        'sections': {
            'ultimas': {
                'name': 'Últimas Notícias',
                'description': 'Todas as notícias de desporto.',
                'start_urls': ['https://www.abola.pt/ultimas-noticias'],
                'filters': {}
            }
        }
    },
    'foxsports': {
        'name': 'Fox Sports',
        'base_url': 'https://www.foxsports.com',
        'language': 'en-US',
        'scraper_class': 'FoxSportsScraper',
        'sections': {
            'nfl': {
                'name': 'NFL News',
                'description': 'Latest NFL news, rumors, and videos from FOX Sports.',
                'start_urls': ['https://www.foxsports.com/nfl/news'],
                'filters': {}
            },
            'college-football': {
                'name': 'College Football News',
                'description': 'Latest College Football news, rumors, and videos from FOX Sports.',
                'start_urls': ['https://www.foxsports.com/college-football/news'],
                'filters': {}
            },
            'mlb': {
                'name': 'MLB News',
                'description': 'Latest MLB news, rumors, and videos from FOX Sports.',
                'start_urls': ['https://www.foxsports.com/mlb/news'],
                'filters': {}
            }
        }
    },
    'cbssports': {
        'name': 'CBS Sports',
        'base_url': 'https://www.cbssports.com',
        'language': 'en-US',
        'scraper_class': 'CBSSportsScraper',
        'sections': {
            'nfl': {
                'name': 'NFL',
                'description': 'Get the latest NFL football news, scores, stats, standings, fantasy games, and more from CBS Sports.',
                'start_urls': ['https://www.cbssports.com/nfl/'],
                'filters': {}
            },
            'college-football': {
                'name': 'College Football',
                'description': 'Get the latest College Football news, scores, stats, standings, fantasy games, and more from CBS Sports.',
                'start_urls': ['https://www.cbssports.com/college-football/'],
                'filters': {}
            },
            'mlb': {
                'name': 'MLB',
                'description': 'Get the latest MLB baseball news, scores, stats, standings, fantasy games, and more from CBS Sports.',
                'start_urls': ['https://www.cbssports.com/mlb/'],
                'filters': {}
            },
            'nba': {
                'name': 'NBA',
                'description': 'Get the latest NBA basketball news, scores, stats, standings, fantasy games, and more from CBS Sports.',
                'start_urls': ['https://www.cbssports.com/nba/'],
                'filters': {}
            }
        }
    }
}

# Alias for easier imports
def validate_source_section(source, section):
    """Validate if source and section combination exists"""
    return get_section_config(source, section) is not None

