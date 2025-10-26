# src/forexfactory/detail_parser.py

"""Utilities for scraping event detail rows from Forex Factory."""

import re

from loguru import logger
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

MAX_RETRIES = 3


def parse_detail_table(driver) -> dict:
    """Parse the detail table when the detail row is expanded."""
    detail_data = {}
    for attempt in range(MAX_RETRIES):
        try:
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((
                    By.XPATH,
                    '//tr[contains(@class,"calendar__details--detail")]//table[@class="calendarspecs"]'
                ))
            )
            all_tables = driver.find_elements(
                By.XPATH,
                '//tr[contains(@class,"calendar__details--detail")]//table[@class="calendarspecs"]'
            )
            if not all_tables:
                logger.warning("No detail_table found.")
                break
            detail_table = all_tables[-1]

            rows = detail_table.find_elements(By.XPATH, './tr')
            for row in rows:
                try:
                    spec_name = row.find_element(By.XPATH, './td[1]').text.strip()
                    spec_desc = row.find_element(By.XPATH, './td[2]').text.strip()
                    detail_data[spec_name] = spec_desc
                except NoSuchElementException:
                    logger.debug("Skipping malformed detail row during parsing.")
            break
        except TimeoutException as exc:
            logger.opt(exception=exc).error("Timeout in parse_detail_table on attempt {}", attempt + 1)
            if attempt < MAX_RETRIES - 1:
                logger.info("Retrying parse_detail_table...")
            else:
                logger.error("Max retries reached while parsing detail table.")
    return detail_data


def detail_data_to_string(detail_data: dict) -> str:
    """Convert dictionary from :func:`parse_detail_table` into a flat string for CSV storage."""
    parts = []
    for key, value in detail_data.items():
        key_clean = re.sub(r'\s+', ' ', key).strip()
        value_clean = re.sub(r'\s+', ' ', value).strip()
        parts.append(f"{key_clean}: {value_clean}")
    return " | ".join(parts)
