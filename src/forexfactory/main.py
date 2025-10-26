# src/forexfactory/main.py

"""Entry point for the Forex Factory scraper CLI."""

import argparse
import sys
from datetime import datetime
from typing import Iterable, Optional, Set

from dateutil.tz import gettz
from loguru import logger

from .incremental import scrape_incremental


def _configure_logging() -> None:
    """Configure Loguru to mirror the previous logging format."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} [{level}] {name}: {message}",
    )


def _normalize_currencies(values: Optional[Iterable[str]]) -> Optional[Set[str]]:
    if not values:
        return None
    normalized = {value.strip().upper() for value in values if value.strip()}
    return normalized or None


def main() -> None:
    _configure_logging()

    parser = argparse.ArgumentParser(description="Forex Factory Scraper (Incremental + pandas)")
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--csv', type=str, default="forex_factory_cache.csv", help='Output CSV file')
    parser.add_argument('--tz', type=str, default="Asia/Tehran", help='Timezone')
    parser.add_argument('--details', action='store_true', help='Scrape details or not')
    parser.add_argument(
        '--currencies',
        nargs='*',
        help='Optional list of currency codes to include (e.g., USD EUR JPY).',
    )

    args = parser.parse_args()

    tz = gettz(args.tz)
    from_date = datetime.fromisoformat(args.start).replace(tzinfo=tz)
    to_date = datetime.fromisoformat(args.end).replace(tzinfo=tz)
    currencies = _normalize_currencies(args.currencies)

    if currencies:
        logger.info("Filtering currencies: {}", ", ".join(sorted(currencies)))

    scrape_incremental(
        from_date,
        to_date,
        args.csv,
        tzname=args.tz,
        scrape_details=args.details,
        currencies=currencies,
    )


if __name__ == "__main__":
    main()
