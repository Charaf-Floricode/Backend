import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

import pandas as pd


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("bio_certificate")

BIO_CERT_URL = "https://webgate.ec.europa.eu/tracesnt/directory/public/bio?panelType=ORGANIC_OPERATOR"

# Environment variables with sane defaults
CHROME_BINARY = os.getenv("CHROME_BIN")  # optional
CHROME_DRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")  # optional
OUTPUT_DIR = Path(os.getenv("BIO_CERT_OUT", "data")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _get_chrome_driver(headless: bool = True) -> webdriver.Chrome:
    """Create and return a configured Chrome WebDriver."""
    opts = Options()
    if headless:
        # the new headless mode is more stable
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    if CHROME_BINARY:
        opts.binary_location = CHROME_BINARY

    try:
        if CHROME_DRIVER_PATH and Path(CHROME_DRIVER_PATH).exists():
            driver = webdriver.Chrome(options=opts, executable_path=CHROME_DRIVER_PATH)
        else:
            # Fallback to Selenium Manager (Selenium >= 4.10) which auto-downloads a driver
            driver = webdriver.Chrome(options=opts)
    except WebDriverException as exc:
        logger.error("Failed to launch ChromeDriver: %s", exc)
        raise

    return driver


def _capture_artifacts(driver: webdriver.Chrome, prefix: str) -> None:
    """Save screenshot and page source to help post-mortem analysis."""
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    screenshot_path = OUTPUT_DIR / f"{prefix}_{ts}.png"
    html_path = OUTPUT_DIR / f"{prefix}_{ts}.html"
    driver.save_screenshot(str(screenshot_path))
    html_path.write_text(driver.page_source, encoding="utf-8")
    logger.info("Saved debug artifacts to %s and %s", screenshot_path, html_path)


def _wait_click(wait: WebDriverWait, by: By, selector: str, desc: str):
    """Wait for element to be clickable and click it. Raises TimeoutException on failure."""
    logger.debug("Waiting for clickable: %s", desc)
    element = wait.until(EC.element_to_be_clickable((by, selector)))
    element.click()
    logger.debug("Clicked: %s", desc)


def scrape_to_dataframe(headless: bool = True) -> pd.DataFrame:
    """Scrape the Traces Organic Certificate directory and return a DataFrame."""
    driver = _get_chrome_driver(headless=headless)
    wait = WebDriverWait(driver, timeout=45)

    try:
        logger.info("Navigating to %s", BIO_CERT_URL)
        driver.get(BIO_CERT_URL)

        # 1. Open the advanced search panel using a stable data attribute
        _wait_click(
            wait,
            By.CSS_SELECTOR,
            "button[data-test='advancedSearch']",
            "Advanced Search button",
        )

        # 2. Click search without changing filters to load all rows
        _wait_click(
            wait,
            By.CSS_SELECTOR,
            "button[data-test='searchBtn']",
            "Search button",
        )

        # 3. Wait until table rows are present
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table[data-test='resultsTable'] tbody tr")
            )
        )

        rows = driver.find_elements(By.CSS_SELECTOR, "table[data-test='resultsTable'] tbody tr")
        if not rows:
            raise RuntimeError("No rows scraped – possible site change or block.")

        records: List[Dict[str, str]] = []
        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            records.append(
                {
                    "operator": cells[0].text.strip(),
                    "country": cells[1].text.strip(),
                    "control_body": cells[2].text.strip(),
                    "certificate": cells[3].text.strip(),
                    "scope": cells[4].text.strip(),
                    "validity": cells[5].text.strip(),
                }
            )

        df = pd.DataFrame(records)
        logger.info("Scraped %d certificate rows", len(df))
        return df

    except TimeoutException as exc:
        logger.error("Timeout while scraping: %s", exc)
        _capture_artifacts(driver, "timeout_error")
        raise
    except Exception as exc:
        logger.error("Unhandled exception: %s", exc)
        _capture_artifacts(driver, "generic_error")
        raise
    finally:
        driver.quit()


def save_dataframe_to_excel(df: pd.DataFrame, output_path: Path) -> None:
    """Save DataFrame to an Excel file."""
    if df.empty:
        raise ValueError("DataFrame is empty – refusing to write empty Excel.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    logger.info("Written Excel to %s", output_path)


def main() -> None:
    df = scrape_to_dataframe(headless=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"bio_certificates_{timestamp}.xlsx"
    save_dataframe_to_excel(df, output_file)


if __name__ == "__main__":
    main()
