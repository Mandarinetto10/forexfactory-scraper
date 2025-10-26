# src/forexfactory/scraper.py

"""Core scraping functionality for Forex Factory."""

import re
import time
from datetime import datetime, timedelta
from typing import Iterable, Optional, Set

import pandas as pd
import undetected_chromedriver as uc
from loguru import logger
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

from .csv_util import ensure_csv_header, merge_new_data, read_existing_data, write_data_to_csv
from .detail_parser import detail_data_to_string, parse_detail_table


def normalize_impact(raw_impact: str) -> str:
    """Return only the impact level from the tooltip text."""
    if not raw_impact:
        return ""
    words = raw_impact.strip().split()
    if not words:
        return ""
    level = words[0].strip().rstrip(':')
    if level.isupper():
        level = level.capitalize()
    return level


def parse_calendar_day(
    driver,
    the_date: datetime,
    scrape_details: bool = False,
    existing_df: Optional[pd.DataFrame] = None,
    currency_filter: Optional[Set[str]] = None,
) -> pd.DataFrame:
    """Scrape data for a single day and return it as a DataFrame."""
    date_str = the_date.strftime('%b%d.%Y').lower()
    url = f"https://www.forexfactory.com/calendar?day={date_str}"
    logger.info("Scraping URL: {}", url)
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.XPATH, '//table[contains(@class,"calendar__table")]'))
        )
    except TimeoutException:
        logger.warning("Page did not load for day {}", the_date.date())
        return pd.DataFrame(columns=["DateTime", "Currency", "Impact", "Event", "Actual", "Forecast", "Previous", "Detail"])

    rows = driver.find_elements(By.XPATH, '//tr[contains(@class,"calendar__row")]')
    data_list = []
    current_day = the_date

    for row in rows:
        row_class = row.get_attribute("class")
        if "day-breaker" in row_class or "no-event" in row_class:
            continue

        try:
            time_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__time")]')
            currency_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__currency")]')
            impact_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__impact")]')
            event_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__event")]')
            actual_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__actual")]')
            forecast_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__forecast")]')
            previous_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__previous")]')
        except NoSuchElementException:
            continue

        time_text = time_el.text.strip()
        currency_text = currency_el.text.strip()

        if currency_filter and currency_text.upper() not in currency_filter:
            continue

        impact_text = ""
        try:
            impact_span = impact_el.find_element(By.XPATH, './/span')
            impact_text = impact_span.get_attribute("title") or ""
        except Exception:
            impact_text = impact_el.text.strip()
        impact_text = normalize_impact(impact_text)

        event_text = event_el.text.strip()
        actual_text = actual_el.text.strip()
        forecast_text = forecast_el.text.strip()
        previous_text = previous_el.text.strip()

        event_dt = current_day
        time_lower = time_text.lower()
        if "day" in time_lower:
            event_dt = event_dt.replace(hour=23, minute=59, second=59)
        elif "data" in time_lower:
            event_dt = event_dt.replace(hour=0, minute=0, second=1)
        else:
            match = re.match(r'(\d{1,2}):(\d{2})(am|pm)', time_lower)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                ampm = match.group(3)
                if ampm == 'pm' and hour < 12:
                    hour += 12
                if ampm == 'am' and hour == 12:
                    hour = 0
                event_dt = event_dt.replace(hour=hour, minute=minute, second=0)

        detail_str = ""
        if scrape_details:
            if existing_df is not None:
                matched = existing_df[
                    (existing_df["DateTime"] == event_dt.isoformat()) &
                    (existing_df["Currency"].str.strip() == currency_text) &
                    (existing_df["Event"].str.strip() == event_text)
                ]
                if not matched.empty:
                    existing_detail = str(matched.iloc[0]["Detail"]).strip() if pd.notnull(matched.iloc[0]["Detail"]) else ""
                    if existing_detail:
                        detail_str = existing_detail

            if not detail_str:
                try:
                    open_link = row.find_element(By.XPATH, './/td[contains(@class,"calendar__detail")]/a')
                    driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", open_link)
                    time.sleep(1)
                    open_link.click()
                    WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.XPATH, '//tr[contains(@class,"calendar__details--detail")]'))
                    )
                    detail_data = parse_detail_table(driver)
                    detail_str = detail_data_to_string(detail_data)
                    try:
                        close_link = row.find_element(By.XPATH, './/a[@title="Close Detail"]')
                        close_link.click()
                    except Exception:
                        logger.debug("Unable to close detail dialog cleanly for event {}", event_text)
                except Exception as exc:  # pragma: no cover - best-effort detail scraping
                    logger.opt(exception=exc).warning("Failed to scrape detail for event {}", event_text)

        data_list.append({
            "DateTime": event_dt.isoformat(),
            "Currency": currency_text,
            "Impact": impact_text,
            "Event": event_text,
            "Actual": actual_text,
            "Forecast": forecast_text,
            "Previous": previous_text,
            "Detail": detail_str,
        })

    return pd.DataFrame(data_list)


def scrape_day(
    driver,
    the_date: datetime,
    existing_df: pd.DataFrame,
    scrape_details: bool = False,
    currency_filter: Optional[Set[str]] = None,
) -> pd.DataFrame:
    """Re-scrape a single day, using existing data for detail caching."""
    return parse_calendar_day(
        driver,
        the_date,
        scrape_details=scrape_details,
        existing_df=existing_df,
        currency_filter=currency_filter,
    )


def scrape_range_pandas(
    from_date: datetime,
    to_date: datetime,
    output_csv: str,
    tzname: str = "Asia/Tehran",
    scrape_details: bool = False,
    currencies: Optional[Iterable[str]] = None,
) -> None:
    """Scrape the Forex Factory calendar for a date range and persist to CSV."""
    ensure_csv_header(output_csv)
    existing_df = read_existing_data(output_csv)

    driver = None
    try:
        driver = uc.Chrome()
        driver.set_window_size(1400, 1000)

        currency_filter = {code.upper() for code in currencies} if currencies else None
        day_count = (to_date - from_date).days + 1
        logger.info(
            "Scraping from {} to {} for {} days (details: {}, tz: {}, currencies: {}).",
            from_date.date(),
            to_date.date(),
            day_count,
            scrape_details,
            tzname,
            ", ".join(sorted(currency_filter)) if currency_filter else "ALL",
        )

        total_new = 0

        for offset in tqdm(range(day_count), desc="Scraping days", unit="day"):
            current_day = from_date + timedelta(days=offset)
            logger.info("Scraping day {}...", current_day.strftime('%Y-%m-%d'))
            df_new = scrape_day(
                driver,
                current_day,
                existing_df,
                scrape_details=scrape_details,
                currency_filter=currency_filter,
            )

            if df_new.empty:
                continue

            merged_df = merge_new_data(existing_df, df_new)
            new_rows = len(merged_df) - len(existing_df)
            if new_rows > 0:
                logger.info("Added/Updated {} rows for {}", new_rows, current_day.date())
            existing_df = merged_df
            total_new += new_rows
            write_data_to_csv(existing_df, output_csv)

        write_data_to_csv(existing_df, output_csv)
        logger.info("Done. Total new/updated rows: {}", total_new)
    finally:
        if driver is not None:
            try:
                driver.quit()
                logger.info("Chrome WebDriver closed successfully.")
            except OSError as exc:
                logger.debug("Ignored OSError during WebDriver quit: {}", exc)
            except Exception as exc:
                logger.opt(exception=exc).error("Error closing WebDriver")
            finally:
                try:
                    driver.quit = lambda *args, **kwargs: None
                    driver.close = lambda *args, **kwargs: None
                except Exception:
                    pass
                try:
                    del driver
                except Exception:
                    pass
                import gc

                gc.collect()
