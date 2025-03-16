"""
config.py

This module provides configuration constants for the cache_manager package,
centralizing settings for cache operations and logging in the business compliance domain.
"""

from pathlib import Path

# Cache configuration
DEFAULT_CACHE_FOLDER = Path(__file__).parent.parent / "cache"
CACHE_TTL_DAYS = 90
DATE_FORMAT = "%Y%m%d"  # e.g., "20250315"
MANIFEST_FILE = "manifest.txt"

# Logging configuration
LOG_LEVEL = "WARNING"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s" 