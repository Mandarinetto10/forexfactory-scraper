# src/forexfactory/csv_util.py

"""CSV utilities for the Forex Factory scraper."""

import os

import pandas as pd
from loguru import logger

# Define the CSV columns
CSV_COLUMNS = ["DateTime", "Currency", "Impact", "Event", "Actual", "Forecast", "Previous", "Detail"]


def ensure_csv_header(csv_file: str) -> None:
    """Ensure that the CSV file exists with the proper header."""
    if not os.path.exists(csv_file):
        logger.debug("Creating CSV file with header at {}", csv_file)
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(csv_file, index=False)


def read_existing_data(csv_file: str) -> pd.DataFrame:
    """Read the existing CSV data and return a DataFrame with the defined columns."""
    if os.path.exists(csv_file):
        try:
            df = pd.read_csv(csv_file, dtype=str)
            for col in CSV_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            return df[CSV_COLUMNS]
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Error reading CSV {}", csv_file)
            return pd.DataFrame(columns=CSV_COLUMNS)
    return pd.DataFrame(columns=CSV_COLUMNS)


def write_data_to_csv(df: pd.DataFrame, csv_file: str) -> None:
    """Write final merged data to CSV, overwriting it."""
    df = df.sort_values(by="DateTime", ascending=True)
    df.to_csv(csv_file, index=False)
    logger.info("Wrote {} rows to {}", len(df), csv_file)


def merge_new_data(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """Merge new data into the existing DataFrame."""
    if existing_df.empty:
        return new_df

    def add_unique_key(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['unique_key'] = (
            df["DateTime"].astype(str).str.strip() + "_" +
            df["Currency"].astype(str).str.strip() + "_" +
            df["Event"].astype(str).str.strip()
        )
        return df

    existing_df = add_unique_key(existing_df)
    new_df = add_unique_key(new_df)

    existing_df.set_index('unique_key', inplace=True)
    new_df.set_index('unique_key', inplace=True)

    new_rows_list = []
    for key, new_row in new_df.iterrows():
        if key in existing_df.index:
            existing_detail = str(existing_df.at[key, "Detail"]).strip() if pd.notna(existing_df.at[key, "Detail"]) else ""
            new_detail = str(new_row["Detail"]).strip() if pd.notna(new_row["Detail"]) else ""
            if not existing_detail and new_detail:
                existing_df.at[key, "Detail"] = new_detail
        else:
            new_rows_list.append(new_row)

    if new_rows_list:
        new_rows_df = pd.DataFrame(new_rows_list)
        existing_df = pd.concat([existing_df, new_rows_df])

    merged_df = existing_df.reset_index(drop=True)
    merged_df = merged_df[CSV_COLUMNS]
    return merged_df
