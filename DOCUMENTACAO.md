
# Documentação Completa da Automação de Feeds RSS/Atom Multi-Fonte

## 📋 Visão Geral

Este sistema é uma aplicação Flask que automatiza a coleta de notícias de múltiplas fontes esportivas brasileiras e internacionais, gerando feeds RSS e Atom padronizados. A automação funciona 24/7 coletando, processando e disponibilizando notícias através de APIs REST.

## 🎯 Objetivo

Criar feeds RSS/Atom não oficiais para portais de notícias esportivas que não possuem feeds nativos ou têm feeds limitados, permitindo que usuários acompanhem notícias através de leitores de feed como Feedly, Inoreader, etc.

## 🔧 Como Funciona a Automação

### 1. **Coleta de Dados (Web Scraping)**
- **Frequência**: A cada 10 minutos
- **Frequência**: A cada 5 minutos
- **Método**: Web scraping responsável com delays entre requisições
- **Respeito ao robots.txt**: Verificação automática de permissões
- **Extração de metadados**: Utiliza JSON-LD estruturado quando disponível
- **Fallback**: Meta tags HTML quando JSON-LD não está disponível

### 2. **Processamento e Armazenamento**
- **Banco de dados**: SQLite com deduplicação por URL
- **Normalização**: Padronização de datas, limpeza de URLs de imagem
- **Filtragem**: Sistema de filtros por autor e termos excluídos
- **Indexação**: Índices otimizados para consultas por data e fonte

### 3. **Geração de Feeds**
- **Formatos**: RSS 2.0 e Atom 1.0
- **Cache**: 15 minutos de cache HTTP
- **Ordenação**: Notícias mais recentes primeiro
- **Metadados ricos**: Incluindo imagens como enclosures

## 📰 Fontes de Notícias Configuradas

### LANCE! (lance.com.br)
**URLs de Origem:**
- https://www.lance.com.br/futebol-nacional/mais-noticias
- https://www.lance.com.br/futebol-internacional/mais-noticias
- https://www.lance.com.br/libertadores/mais-noticias
- https://www.lance.com.br/copa-do-mundo/mais-noticias
- https://www.lance.com.br/champions-league/mais-noticias
- https://www.lance.com.br/premier-league/mais-noticias
- https://www.lance.com.br/la-liga/mais-noticias
- https://www.lance.com.br/bundesliga/mais-noticias
- https://www.lance.com.br/tudo-sobre/campeonato-italiano
- https://www.lance.com.br/ligue-1/mais-noticias

**Feeds RSS Gerados:**
```
https://[SEU-DOMINIO]/feeds/lance/futebol-nacional/rss
https://[SEU-DOMINIO]/feeds/lance/futebol-internacional/rss
https://[SEU-DOMINIO]/feeds/lance/libertadores/rss
https://[SEU-DOMINIO]/feeds/lance/copa-do-mundo/rss
https://[SEU-DOMINIO]/feeds/lance/champions-league/rss
https://[SEU-DOMINIO]/feeds/lance/premier-league/rss
https://[SEU-DOMINIO]/feeds/lance/la-liga/rss
https://[SEU-DOMINIO]/feeds/lance/bundesliga/rss
https://[SEU-DOMINIO]/feeds/lance/campeonato-italiano/rss
https://[SEU-DOMINIO]/feeds/lance/ligue-1/rss
```

**Feeds Atom Gerados:**
```
https://[SEU-DOMINIO]/feeds/lance/futebol-nacional/atom
https://[SEU-DOMINIO]/feeds/lance/futebol-internacional/atom
https://[SEU-DOMINIO]/feeds/lance/libertadores/atom
https://[SEU-DOMINIO]/feeds/lance/copa-do-mundo/atom
https://[SEU-DOMINIO]/feeds/lance/champions-league/atom
https://[SEU-DOMINIO]/feeds/lance/premier-league/atom
https://[SEU-DOMINIO]/feeds/lance/la-liga/atom
https://[SEU-DOMINIO]/feeds/lance/bundesliga/atom
https://[SEU-DOMINIO]/feeds/lance/campeonato-italiano/atom
https://[SEU-DOMINIO]/feeds/lance/ligue-1/atom
```

### Gazeta Esportiva (gazetaesportiva.com)
**URL de Origem:**
- https://www.gazetaesportiva.com/todas-as-noticias/

**Feeds Gerados:**
```
RSS: https://[SEU-DOMINIO]/feeds/gazeta/todas-noticias/rss
Atom: https://[SEU-DOMINIO]/feeds/gazeta/todas-noticias/atom
```

### UOL Esporte (uol.com.br)
**URL de Origem:**
- https://www.uol.com.br/esporte/futebol/ultimas/

**Feeds Gerados:**
```
RSS: https://[SEU-DOMINIO]/feeds/uol/futebol/rss
Atom: https://[SEU-DOMINIO]/feeds/uol/futebol/atom
```

**Filtros Aplicados:**
- Exclusão de artigos da "Gazeta Esportiva" (evita duplicatas)

### Globo Esporte (ge.globo.com)
**URLs de Origem:**
- https://ge.globo.com/ (Geral)
- https://ge.globo.com/futebol/
- https://ge.globo.com/futebol/brasileirao-serie-a/
- https://ge.globo.com/futebol/libertadores/
- https://ge.globo.com/futebol/futebol-internacional/

**Feeds Gerados:**
```
RSS:
https://[SEU-DOMINIO]/feeds/globo/geral/rss
https://[SEU-DOMINIO]/feeds/globo/futebol/rss
https://[SEU-DOMINIO]/feeds/globo/brasileirao/rss
https://[SEU-DOMINIO]/feeds/globo/libertadores/rss
https://[SEU-DOMINIO]/feeds/globo/internacional/rss

Atom:
https://[SEU-DOMINIO]/feeds/globo/geral/atom
https://[SEU-DOMINIO]/feeds/globo/futebol/atom
https://[SEU-DOMINIO]/feeds/globo/brasileirao/atom
https://[SEU-DOMINIO]/feeds/globo/libertadores/atom
https://[SEU-DOMINIO]/feeds/globo/internacional/atom
```

## 🤖 Detalhes da Automação

### Agendador (Scheduler)
- **Biblioteca**: APScheduler
- **Intervalo**: 5 minutos
- **Proteção**: Mutex para evitar execuções simultâneas
- **Logs**: Registro detalhado de todas as operações

### Processo de Scraping
1. **Listagem de páginas**: Coleta links de artigos das páginas de listagem
2. **Paginação**: Segue links de "próxima página" até 2 páginas por seção
3. **Extração individual**: Processa cada artigo individualmente
4. **Deduplicação**: Verifica se o artigo já existe no banco
5. **Filtragem**: Aplica filtros configurados
6. **Armazenamento**: Salva no SQLite

### Extração de Metadados
```python
# Ordem de prioridade para extração:
1. JSON-LD estruturado (@type: Article/NewsArticle)
2. Meta tags Open Graph
3. Meta tags HTML padrão
4. Fallback para título da página
```

### Sistema de Cache
- **HTTP Cache**: 15 minutos nos headers dos feeds
- **Refresh forçado**: Parâmetro `?refresh=1`
- **Cache de robots.txt**: Evita consultas desnecessárias

## 📊 Estrutura dos Dados

### Esquema do Banco de Dados
```sql
CREATE TABLE articles (
    url TEXT PRIMARY KEY,           -- URL única do artigo
    title TEXT NOT NULL,           -- Título do artigo
    description TEXT,              -- Descrição/resumo
    image TEXT,                    -- URL da imagem principal
    author TEXT,                   -- Autor do artigo
    date_published TIMESTAMP,      -- Data de publicação original
    date_modified TIMESTAMP,       -- Data de última modificação
    fetched_at TIMESTAMP NOT NULL, -- Quando foi coletado
    created_at TIMESTAMP,          -- Quando foi inserido no DB
    updated_at TIMESTAMP,          -- Última atualização no DB
    source TEXT,                   -- Fonte (lance, gazeta, uol, etc.)
    section TEXT,                  -- Seção (futebol, libertadores, etc.)
    site TEXT                      -- Domínio do site
);
```

### Exemplo de Artigo Processado
```json
{
    "url": "https://www.lance.com.br/flamengo/noticia/...",
    "title": "Flamengo confirma contratação de novo técnico",
    "description": "Clube carioca anuncia chegada do treinador...",
    "image": "https://cdn.lance.com.br/img/noticia.jpg",
    "author": "João Silva",
    "date_published": "2025-01-16T14:30:00Z",
    "date_modified": "2025-01-16T15:00:00Z",
    "fetched_at": "2025-01-16T15:05:00Z",
    "source": "lance",
    "section": "futebol-nacional",
    "site": "lance.com.br"
}
```

## 🔗 API de Feeds

### Endpoints Dinâmicos
```
Padrão: /feeds/{fonte}/{seção}/{formato}

Exemplos:
/feeds/lance/futebol-nacional/rss
/feeds/gazeta/todas-noticias/atom
/feeds/uol/futebol/rss
```

### Parâmetros de Query
- `limit` - Número de artigos (padrão: 30, máximo: 100)
- `q` - Filtro por termo de busca
- `refresh` - Força nova coleta (1 para ativar)

### Exemplos de URLs Completas
```
# Feed básico
https://[SEU-DOMINIO]/feeds/lance/libertadores/rss

# Feed limitado a 10 artigos
https://[SEU-DOMINIO]/feeds/lance/libertadores/rss?limit=10

# Feed filtrado por "Palmeiras"
https://[SEU-DOMINIO]/feeds/lance/libertadores/rss?q=Palmeiras

# Feed com refresh forçado
https://[SEU-DOMINIO]/feeds/lance/libertadores/rss?refresh=1
```

## 🛡️ Aspectos de Segurança e Ética

### Web Scraping Responsável
- **Delays**: 0.3 a 1 segundo entre requisições
- **User-Agent**: Identificação clara como bot de feed
- **Robots.txt**: Verificação automática de permissões
- **Rate limiting**: Máximo 20 artigos por execução para evitar sobrecarga

### Filtros de Conteúdo
- **Exclusão de autores**: Evita duplicatas entre fontes
- **Filtros por termo**: Remove conteúdo indesejado
- **Validação de dados**: Verifica integridade dos metadados

## 📈 Monitoramento e Logs

### Endpoints de Status
- `GET /health` - Status do sistema e métricas
- `GET /admin/stats?key=CHAVE` - Estatísticas detalhadas
- `GET /admin/refresh?key=CHAVE` - Refresh manual

### Logs Detalhados
```
INFO - Scheduler started - refresh every 10 minutes
INFO - Starting multi-source feed refresh
INFO - Scraping lance/futebol-nacional from https://...
INFO - Found 25 article links on page 1
INFO - Processing article 1/20: https://...
INFO - Stored article: Título do artigo
INFO - Scraped 15 new articles for lance/futebol-nacional
```

### Métricas Disponíveis
- Total de artigos no banco
- Artigos coletados nas últimas 24h
- Artigos coletados na última semana
- Artigos com imagens
- Top 10 autores por volume

## 🔄 Fluxo Completo da Automação

```
1. AGENDADOR (a cada 10 min)
   ↓
2. MULTI-SOURCE REFRESH
   ↓
3. PARA CADA FONTE/SEÇÃO:
   │
   ├── Buscar páginas de listagem
   ├── Extrair links de artigos (máx 20)
   ├── Para cada artigo:
   │   ├── Verificar se já existe
   │   ├── Fazer scraping dos metadados
   │   ├── Aplicar filtros
   │   ├── Salvar no banco
   │   └── Delay de 0.3s
   │
   └── Delay de 2s entre seções
   ↓
4. FEED GENERATION (sob demanda)
   ├── Consultar banco por fonte/seção
   ├── Aplicar filtros adicionais
   ├── Ordenar por data (mais recente primeiro)
   ├── Gerar XML (RSS ou Atom)
   └── Retornar com cache de 15 min
```

## 🚀 Como Usar os Feeds

### Em Leitores de RSS
1. Copie a URL do feed desejado
2. Cole no seu leitor RSS (Feedly, Inoreader, etc.)
3. Os artigos serão atualizados automaticamente

### Integração via API
```python
import requests
import feedparser

# Buscar feed
response = requests.get('https://[SEU-DOMINIO]/feeds/lance/libertadores/rss')
feed = feedparser.parse(response.text)

# Processar artigos
for entry in feed.entries:
    print(f"Título: {entry.title}")
    print(f"Link: {entry.link}")
    print(f"Data: {entry.published}")
    print(f"Descrição: {entry.description}")
    print("---")
```

## 🔧 Configuração e Personalização

### Adicionando Novas Fontes
1. Criar scraper específico em `app/[fonte]_scraper.py`
2. Adicionar configuração em `app/sources_config.py`
3. Registrar classe em `app/scraper_factory.py`

### Modificando Filtros
```python
# Em sources_config.py
'filters': {
    'exclude_authors': ['Autor Indesejado'],
    'exclude_terms': ['termo-bloqueado']
}
```

### Ajustando Intervalos
```python
# Em scheduler.py
refresh_interval_minutes=10  # Alterar conforme necessário
```

## 📝 Logs de Exemplo

```
2025-01-16 15:00:00 - INFO - Starting multi-source feed refresh
2025-01-16 15:00:01 - INFO - Refreshing lance/futebol-nacional
2025-01-16 15:00:01 - INFO - Scraping from: https://www.lance.com.br/futebol-nacional/mais-noticias
2025-01-16 15:00:02 - INFO - Found 25 article links on page 1
2025-01-16 15:00:03 - INFO - Processing article 1/20: https://...
2025-01-16 15:00:04 - INFO - Stored article: Flamengo anuncia contratação
2025-01-16 15:00:15 - INFO - Added 15 new articles for lance/futebol-nacional
2025-01-16 15:00:17 - INFO - Refreshing gazeta/todas-noticias
2025-01-16 15:00:30 - INFO - Multi-source refresh completed - 45 new articles
```

## 🎯 URLs Finais dos Feeds (Substitua [SEU-DOMINIO])

### LANCE! Feeds
```
RSS:
- https://[SEU-DOMINIO]/feeds/lance/futebol-nacional/rss
- https://[SEU-DOMINIO]/feeds/lance/futebol-internacional/rss
- https://[SEU-DOMINIO]/feeds/lance/libertadores/rss
- https://[SEU-DOMINIO]/feeds/lance/copa-do-mundo/rss
- https://[SEU-DOMINIO]/feeds/lance/champions-league/rss
- https://[SEU-DOMINIO]/feeds/lance/premier-league/rss
- https://[SEU-DOMINIO]/feeds/lance/la-liga/rss
- https://[SEU-DOMINIO]/feeds/lance/bundesliga/rss
- https://[SEU-DOMINIO]/feeds/lance/campeonato-italiano/rss
- https://[SEU-DOMINIO]/feeds/lance/ligue-1/rss

Atom:
- https://[SEU-DOMINIO]/feeds/lance/futebol-nacional/atom
- https://[SEU-DOMINIO]/feeds/lance/futebol-internacional/atom
- https://[SEU-DOMINIO]/feeds/lance/libertadores/atom
- https://[SEU-DOMINIO]/feeds/lance/copa-do-mundo/atom
- https://[SEU-DOMINIO]/feeds/lance/champions-league/atom
- https://[SEU-DOMINIO]/feeds/lance/premier-league/atom
- https://[SEU-DOMINIO]/feeds/lance/la-liga/atom
- https://[SEU-DOMINIO]/feeds/lance/bundesliga/atom
- https://[SEU-DOMINIO]/feeds/lance/campeonato-italiano/atom
- https://[SEU-DOMINIO]/feeds/lance/ligue-1/atom
```

### Outros Feeds
```
RSS:
- https://[SEU-DOMINIO]/feeds/gazeta/todas-noticias/rss
- https://[SEU-DOMINIO]/feeds/uol/futebol/rss
- https://[SEU-DOMINIO]/feeds/globo/geral/rss
- https://[SEU-DOMINIO]/feeds/globo/futebol/rss
- https://[SEU-DOMINIO]/feeds/globo/brasileirao/rss
- https://[SEU-DOMINIO]/feeds/globo/libertadores/rss
- https://[SEU-DOMINIO]/feeds/globo/internacional/rss

Atom:
- https://[SEU-DOMINIO]/feeds/gazeta/todas-noticias/atom
- https://[SEU-DOMINIO]/feeds/uol/futebol/atom
- https://[SEU-DOMINIO]/feeds/globo/geral/atom
- https://[SEU-DOMINIO]/feeds/globo/futebol/atom
- https://[SEU-DOMINIO]/feeds/globo/brasileirao/atom
- https://[SEU-DOMINIO]/feeds/globo/libertadores/atom
- https://[SEU-DOMINIO]/feeds/globo/internacional/atom
```

---

**⚠️ Aviso Legal**: Este projeto é apenas para fins educativos. Todo o conteúdo coletado pertence às respectivas fontes originais. O sistema implementa práticas responsáveis de web scraping respeitando robots.txt e implementando delays apropriados.
