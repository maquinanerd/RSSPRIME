import os
import logging
from app.server import app

# Configure logging for production
if os.environ.get('FLASK_ENV') != 'development':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5000, debug=True)
