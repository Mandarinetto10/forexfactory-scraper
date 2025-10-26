# src/forexfactory/incremental.py

"""Utilities orchestrating incremental scraping runs."""

from datetime import datetime
from typing import Iterable, Optional

from loguru import logger

from .scraper import scrape_range_pandas


def scrape_incremental(
    from_date: datetime,
    to_date: datetime,
    output_csv: str,
    tzname: str = "Asia/Tehran",
    scrape_details: bool = False,
    currencies: Optional[Iterable[str]] = None,
) -> None:
    """Scrape the requested range, delegating to the pandas-based scraper."""
    logger.info(
        "Starting incremental scrape from {} to {} (details: {}, tz: {})",
        from_date.date(),
        to_date.date(),
        scrape_details,
        tzname,
    )

    scrape_range_pandas(
        from_date,
        to_date,
        output_csv,
        tzname=tzname,
        scrape_details=scrape_details,
        currencies=currencies,
    )
