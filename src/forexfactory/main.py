# src/forexfactory/main.py

import sys
import os
import argparse
from datetime import datetime
from dateutil.tz import gettz
from loguru import logger

from .incremental import scrape_incremental

LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
LOG_ROTATION = "500 MB"
LOG_RETENTION = "30 days"

def setup_logging(log_file: str = None):
    """Configura logging con loguru"""
    logger.remove()
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level="INFO"
    )
    
    if log_file:
        logger.add(
            log_file,
            format=LOG_FORMAT,
            level="DEBUG",
            rotation=LOG_ROTATION,
            retention=LOG_RETENTION
        )

def main():
    parser = argparse.ArgumentParser(description="Forex Factory Scraper (Incremental + pandas)")
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--csv', type=str, default="forex_factory_cache.csv", help='Output CSV file')
    parser.add_argument('--tz', type=str, default="Asia/Tehran", help='Timezone')
    parser.add_argument('--details', action='store_true', help='Scrape details or not')
    parser.add_argument('--currencies', type=str, default=None, help='Comma-separated list of currencies to filter (e.g., USD,EUR,JPY)')
    parser.add_argument('--log-file', type=str, default=None, help='Log file path (optional)')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_file)

    tz = gettz(args.tz)
    from_date = datetime.fromisoformat(args.start).replace(tzinfo=tz)
    to_date = datetime.fromisoformat(args.end).replace(tzinfo=tz)

    # Parse currencies
    currencies = None
    if args.currencies:
        currencies = set(c.strip().upper() for c in args.currencies.split(','))

    scrape_incremental(from_date, to_date, args.csv, tzname=args.tz, scrape_details=args.details, currencies=currencies)

if __name__ == "__main__":
    main()