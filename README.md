# LANCE! RSS/Atom Feed Generator

Um gerador de feeds RSS e Atom não oficiais para o portal de notícias LANCE! Este projeto é puramente educativo e demonstra técnicas de web scraping responsável e geração de feeds.

## ⚠️ Aviso Importante

Este projeto é apenas para fins educativos. Respeita robots.txt, implementa delays entre requisições e não deve ser usado para fins comerciais. Todo o conteúdo pertence ao portal LANCE!

## 🚀 Funcionalidades

- **Web Scraping Responsável**: Varre as páginas de listagem do LANCE! respeitando robots.txt
- **Extração de Metadados**: Usa JSON-LD para extrair metadados precisos dos artigos
- **Feeds RSS e Atom**: Gera feeds padronizados com enclosures de imagem
- **Banco de Dados SQLite**: Armazena artigos com deduplicação
- **Agendador Automático**: Atualiza feeds a cada 15 minutos
- **Filtragem**: Suporte a filtros por termo de busca
- **Interface Web**: Dashboard com estatísticas e links dos feeds

## 📋 Endpoints

### Feeds
- `GET /feeds/lance/rss.xml` - Feed RSS 2.0
- `GET /feeds/lance/atom.xml` - Feed Atom 1.0

### Utilitários
- `GET /` - Página inicial com documentação
- `GET /health` - Status e métricas do sistema
- `GET /admin/refresh?key=CHAVE` - Atualização manual (requer chave admin)

### Parâmetros de Query

| Parâmetro | Descrição | Padrão | Exemplo |
|-----------|-----------|---------|---------|
| `limit` | Número máximo de artigos | 30 | `?limit=20` |
| `pages` | Páginas para varrer | 3 | `?pages=5` |
| `q` | Filtrar por termo | - | `?q=Flamengo` |
| `source_url` | URL de origem alternativa | /mais-noticias | `?source_url=...` |
| `refresh` | Forçar nova varredura | 0 | `?refresh=1` |

## 🛠 Instalação Local

1. **Clone o repositório**
```bash
git clone <repository-url>
cd lance-feed-generator
