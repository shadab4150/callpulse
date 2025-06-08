import requests
import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

# Configure logging
logger = logging.getLogger("earnings_fetcher")

class EarningsCallFetcher:
    def __init__(self, api_key: str, data_dir: str = "./data/transcripts/"):
        self.api_key = api_key
        self.data_dir = data_dir
        self.base_url = "https://api.api-ninjas.com/v1/earningstranscript"
        self.headers = {"X-Api-Key": self.api_key}
        os.makedirs(self.data_dir, exist_ok=True)
        logger.info(f"Initialized EarningsCallFetcher with data directory: {self.data_dir}")

    def get_transcript(self, ticker: str, year: int, quarter: int, force_refresh: bool = False):
        ticker = ticker.upper()
        filename = self._get_filename(ticker, year, quarter)

        if os.path.exists(filename) and not force_refresh:
            logger.info(f"Using cached transcript for {ticker} {year} Q{quarter}")
            try:
                with open(filename, "r") as f:
                    return True, json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Cached file corrupted, will fetch fresh: {filename}")
            except Exception as e:
                logger.error(f"Error reading cached file: {e}")

        return self._fetch_from_api(ticker, year, quarter)

    def get_last_n_quarters(self, ticker: str, n: int = 4) -> List[Dict[str, Any]]:
        ticker = ticker.upper()
        results = []

        current_date = datetime.now()
        current_year = current_date.year
        current_quarter = (current_date.month - 1) // 3 + 1

        # Try to fetch the last n quarters
        attempts = 0
        quarters_found = 0

        while quarters_found < n and attempts < n * 2:  # Allow for some quarters to be missing
            year = current_year
            quarter = current_quarter - attempts

            # Adjust year and quarter if we go back past Q1
            while quarter <= 0:
                year -= 1
                quarter += 4

            success, data = self.get_transcript(ticker, year, quarter)

            if success and "error" not in data:
                # Add metadata to the result
                data["ticker"] = ticker
                data["year"] = year
                data["quarter"] = quarter
                data["fetch_date"] = datetime.now().isoformat()

                results.append(data)
                quarters_found += 1
                logger.info(f"Found transcript for {ticker} {year} Q{quarter}")
            else:
                logger.warning(f"No transcript available for {ticker} {year} Q{quarter}")

            attempts += 1
            time.sleep(0.0001)  # Add a small delay

        logger.info(f"Found {quarters_found} transcripts for {ticker}")
        return results

    def _get_filename(self, ticker: str, year: int, quarter: int) -> str:
        return os.path.join(self.data_dir, f"{ticker}_{year}_Q{quarter}.json")

    def _fetch_from_api(self, ticker: str, year: int, quarter: int) -> Tuple[bool, Dict[str, Any]]:
        url = f"{self.base_url}?ticker={ticker}&year={year}&quarter={quarter}"

        try:
            logger.info(f"Fetching from API: {ticker} {year} Q{quarter}")
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # Check if we got actual content
                if data and "transcript" in data and data["transcript"]:
                    # Save the transcript to file
                    filename = self._get_filename(ticker, year, quarter)
                    with open(filename, "w") as f:
                        json.dump(data, f)

                    logger.info(f"Successfully saved transcript: {filename}")
                    return True, data
                else:
                    error_msg = f"API returned empty transcript for {ticker} {year} Q{quarter}"
                    logger.warning(error_msg)
                    return False, {"error": error_msg}
            else:
                error_msg = f"API request failed: {response.status_code}, {response.text}"
                logger.error(error_msg)
                return False, {"error": error_msg, "status_code": response.status_code}

        except requests.exceptions.Timeout:
            error_msg = f"API request timed out for {ticker} {year} Q{quarter}"
            logger.error(error_msg)
            return False, {"error": error_msg}

        except Exception as e:
            error_msg = f"Error fetching from API: {str(e)}"
            logger.error(error_msg)
            return False, {"error": error_msg} 