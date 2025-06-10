import os
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

import pandas as pd

# -----------------------------------------------------------------------------
# Logging & configuration
# -----------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("bio_certificate")

BIO_CERT_URL = (
    "https://webgate.ec.europa.eu/tracesnt/directory/public/bio?panelType=ORGANIC_OPERATOR"
)

# Environment variables with sane defaults
CHROME_BINARY = os.getenv("CHROME_BIN")  # optional override
CHROME_DRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")  # optional override
OUTPUT_DIR = Path(os.getenv("BIO_CERT_OUT", "/tmp")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Default Selenium waits (seconds)
PAGE_TIMEOUT = int(os.getenv("BIO_CERT_PAGE_TIMEOUT", "120"))
WAIT_TIMEOUT = int(os.getenv("BIO_CERT_WAIT_TIMEOUT", "60"))
SCROLL_PAUSE = float(os.getenv("BIO_CERT_SCROLL_PAUSE", "1.0"))

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _get_chrome_driver(headless: bool = True) -> webdriver.Chrome:
    """Return a configured Chrome WebDriver (lets Selenium Manager pick driver)."""

    opts = Options()
    if headless:
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
            driver = webdriver.Chrome(options=opts)
    except WebDriverException:
        logger.exception("Failed to launch ChromeDriver")
        raise

    driver.set_page_load_timeout(PAGE_TIMEOUT)
    return driver


def _capture_artifacts(driver: webdriver.Chrome, prefix: str) -> None:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    png = OUTPUT_DIR / f"{prefix}_{ts}.png"
    html = OUTPUT_DIR / f"{prefix}_{ts}.html"
    driver.save_screenshot(str(png))
    html.write_text(driver.page_source, encoding="utf-8")
    logger.info("Saved debug artifacts → %s & %s", png, html)


def _wait_for_loader_gone(wait: WebDriverWait) -> None:
    try:
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".pageLoader")))
        logger.debug("Page loader invisible – ready for interaction")
    except TimeoutException:
        logger.warning("Loader still visible after timeout – proceeding anyway")


def _click_when_clickable(wait: WebDriverWait, locator: Tuple[By, str], desc: str):
    logger.debug("Waiting for %s via %s:%s", desc, locator[0], locator[1])
    elem = wait.until(EC.element_to_be_clickable(locator))
    elem.click()
    logger.debug("Clicked %s", desc)


def _accept_cookies_if_present(driver: webdriver.Chrome, wait: WebDriverWait):
    try:
        btn = wait.until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "a.wt-cck--actions-button, button#onetrust-accept-btn-handler",
                )
            )
        )
        btn.click()
        logger.debug("Cookie banner accepted")
    except TimeoutException:
        pass  # no cookie banner

# -----------------------------------------------------------------------------
# Core scrape logic
# -----------------------------------------------------------------------------

def _scroll_to_load_all(driver: webdriver.Chrome):
    previous = -1
    while True:
        rows = driver.find_elements(By.CSS_SELECTOR, "table#organicOperatorCertificates tbody tr")
        if len(rows) == previous:
            break
        previous = len(rows)
        if rows:
            driver.execute_script("arguments[0].scrollIntoView();", rows[-1])
        else:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
    logger.info("Infinite scroll collected %d rows", previous)


def scrape_to_dataframe(headless: bool = True) -> pd.DataFrame:
    driver = _get_chrome_driver(headless)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    try:
        logger.info("Opening %s", BIO_CERT_URL)
        driver.get(BIO_CERT_URL)

        _wait_for_loader_gone(wait)
        _accept_cookies_if_present(driver, wait)

        # Click the primary "Zoeken" button to fetch results (no filters)
        _click_when_clickable(
            wait,
            (By.XPATH, "//button[@type='submit' and contains(normalize-space(.),'Zoeken')]") ,
            "Search button",
        )

        # Wait until at least one result row appears in the certificates table
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table#organicOperatorCertificates tbody tr")
            )
        )

        _scroll_to_load_all(driver)

        rows = driver.find_elements(By.CSS_SELECTOR, "table#organicOperatorCertificates tbody tr")
        if not rows:
            raise RuntimeError("0 rows scraped – layout or access issue")

        records: List[Dict[str, str]] = []
        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            if len(cells) < 8:
                continue
            records.append(
                {
                    "reference": cells[0].text.strip(),
                    "operator": cells[1].text.strip(),
                    "authority": cells[2].text.strip(),
                    "activities": cells[3].text.strip(),
                    "product_categories": cells[4].text.strip(),
                    "issued_on": cells[5].text.strip(),
                    "expires_on": cells[6].text.strip(),
                }
            )

        df = pd.DataFrame(records)
        logger.info("Scraped %d certificates", len(df))
        return df

    except Exception:
        logger.exception("Scraping failed – capturing artifacts")
        _capture_artifacts(driver, "scrape_error")
        raise
    finally:
        driver.quit()

# -----------------------------------------------------------------------------
# IO helpers
# -----------------------------------------------------------------------------

def save_dataframe_to_excel(df: pd.DataFrame, output_path: Path):
    if df.empty:
        raise ValueError("DataFrame is empty – refusing to save.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    logger.info("Excel written → %s", output_path)


def main():
    df = scrape_to_dataframe(headless=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    save_dataframe_to_excel(df, OUTPUT_DIR / f"bio_certificates_{ts}.xlsx")


if __name__ == "__main__":
    main()
