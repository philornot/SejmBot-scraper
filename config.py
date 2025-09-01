# config.py
"""
Konfiguracja dla SejmBotScraper
"""

import os

# API Configuration
API_BASE_URL = "https://api.sejm.gov.pl"
DEFAULT_TERM = 10  # 10 kadencja

# File paths
BASE_OUTPUT_DIR = "stenogramy_sejm"
LOGS_DIR = "logs"

# Request settings
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1  # sekundy między zapytaniami (żeby być grzecznym dla API)

# Supported formats
TRANSCRIPT_FORMATS = {
    'pdf': '/pdf',
    'html': ''  # individual statements in HTML
}

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Create directories if they don't exist
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
