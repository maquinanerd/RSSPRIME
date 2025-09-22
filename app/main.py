import os
import logging
from .server import app

# A configuração de logging já é feita em server.py, mas garantimos aqui.
logger = logging.getLogger(__name__)

def main():
    """Função principal para iniciar o servidor Flask."""
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    
    # O modo de depuração é ótimo para desenvolvimento.
    # Ele recarrega o servidor automaticamente quando você salva um arquivo.
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() in ("true", "1", "t")

    logger.info(f"Iniciando servidor Flask em http://{host}:{port} (Debug: {debug_mode})")
    app.run(host=host, port=port, debug=debug_mode)

if __name__ == "__main__":
    main()