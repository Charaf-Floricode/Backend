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
PAGE_TIMEOUT = int(os.getenv("BIO_CERT_PAGE_TIMEOUT", "90"))
WAIT_TIMEOUT = int(os.getenv("BIO_CERT_WAIT_TIMEOUT", "60"))
SCROLL_PAUSE = float(os.getenv("BIO_CERT_SCROLL_PAUSE", "1.0"))

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _get_chrome_driver(headless: bool = True) -> webdriver.Chrome:
    """Return a configured Chrome WebDriver (auto‑downloads driver if needed)."""

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
            driver = webdriver.Chrome(options=opts)  # Selenium Manager
    except WebDriverException:
        logger.exception("Failed to launch ChromeDriver")
        raise

    driver.set_page_load_timeout(PAGE_TIMEOUT)
    return driver


def _capture_artifacts(driver: webdriver.Chrome, prefix: str) -> None:
    """Save screenshot + HTML to OUTPUT_DIR with UTC timestamp."""
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


def _click_first(
    wait: WebDriverWait,
    driver: webdriver.Chrome,
    locator_options: List[Tuple[By, str]],
    description: str,
    root=None,
):
    """Attempt to click the first locator that appears, trying all options in order."""
    ctx = root if root is not None else driver
    for by, sel in locator_options:
        try:
            logger.debug("Waiting for %s via %s:%s", description, by, sel)
            elem = wait.until(EC.element_to_be_clickable((by, sel)))
            if root and not root.is_displayed():
                continue  # hidden duplicate inside template
            elem.click()
            logger.debug("Clicked %s via %s", description, sel)
            return
        except TimeoutException:
            continue
    raise TimeoutException(f"Could not find {description} via any locator")


def _accept_cookies_if_present(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    """Click the cookie banner accept button if it exists (non‑blocking)."""
    try:
        cookie_btn = wait.until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "button#onetrust-accept-btn-handler, button[data-testid='uc-accept-all']",
                )
            )
        )
        cookie_btn.click()
        logger.debug("Cookie banner accepted")
    except TimeoutException:
        pass  # No banner


# -----------------------------------------------------------------------------
# Core scrape logic
# -----------------------------------------------------------------------------

def _scroll_to_load_all(driver: webdriver.Chrome) -> None:
    """Scroll inside the results table until no new rows appear."""
    prev_len = -1
    while True:
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        if len(rows) == prev_len:
            break  # no new rows after last scroll
        prev_len = len(rows)
        if rows:
            driver.execute_script("arguments[0].scrollIntoView();", rows[-1])
        else:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
    logger.info("Infinite scroll yielded %d total rows", prev_len)


def scrape_to_dataframe(headless: bool = True) -> pd.DataFrame:
    """Scrape the TRACES organic certificate directory → DataFrame."""

    driver = _get_chrome_driver(headless)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    try:
        logger.info("Navigating → %s", BIO_CERT_URL)
        driver.get(BIO_CERT_URL)

        _wait_for_loader_gone(wait)
        _accept_cookies_if_present(driver, wait)

        # Scope to main listing form – avoids hidden dupes in templates
        listing_form = wait.until(EC.presence_of_element_located((By.ID, "organicOperatorCertificateListingSearch")))

        # Optional: expand Advanced Search (not strictly needed for unfiltered search)
        try:
            _click_first(
                wait,
                driver,
                [
                    (By.CSS_SELECTOR, "button[ng-click='toggleAdvancedSearch()']"),
                    (
                        By.XPATH,
                        "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'advanced search') or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'geavanceerd zoeken')]",
                    ),
                ],
                "Advanced Search button",
                root=listing_form,
            )
        except TimeoutException:
            logger.debug("Advanced Search button not found – continuing without it")

        # Click the main Search (Zoeken) button to run the query
        _click_first(
            wait,
            driver,
            [
                (By.CSS_SELECTOR, "form#organicOperatorCertificateListingSearch button[type='submit'].btn-primary"),
                (By.XPATH, "//button[(@type='submit') and contains(.,'Zoeken')]"),
            ],
            "Search button",
            root=listing_form,
        )

        # Wait for at least one result row
        wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "table tbody tr",
                )
            )
        )

        # Infinite scroll until all rows are loaded
        _scroll_to_load_all(driver)

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        if not rows:
            raise RuntimeError("0 rows scraped – layout change or access blocked.")

        records: List[Dict[str, str]] = []
        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            if len(cells) < 6:
                continue  # skip malformed rows
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
        logger.error("Timeout while scraping → %s", exc.msg if hasattr(exc, 'msg') else exc)
        _capture_artifacts(driver, "timeout_error")
        raise
    except Exception:
        logger.exception("Unhandled scraping error")
        _capture_artifacts(driver, "generic_error")
        raise
    finally:
        driver.quit()


# -----------------------------------------------------------------------------
# IO helpers
# -----------------------------------------------------------------------------

def save_dataframe_to_excel(df: pd.DataFrame, output_path: Path) -> None:
    if df.empty:
        raise ValueError("DataFrame empty – refusing to write empty Excel file.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    logger.info("Excel saved → %s", output_path)


def main() -> None:
    df = scrape_to_dataframe(headless=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    save_dataframe_to_excel(df, OUTPUT_DIR / f"bio_certificates_{ts}.xlsx")


if __name__ == "__main__":
    main()
