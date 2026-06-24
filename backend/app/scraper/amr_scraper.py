"""
PEA AMR scraper - adapted from the original AMR_REE.py script.

What changed vs the original script:
  - AMR_USERNAME / AMR_PASSWORD / START_DATE / END_DATE / DOWNLOAD_DIR are no
    longer hardcoded globals - they're passed in per job.
  - The terminal StatusDisplay class is replaced with a `on_progress`
    callback so the web backend can push percentages to the frontend.
  - No PROGRESS_FILE / FAILED_LOG resume-from-disk bookkeeping - each web job
    is a single, fresh run.
  - The login/meter-discovery/popup-handling/download logic is otherwise the
    same approach as the original (this is the part that's fragile and
    specific to the AMR site, so it's kept as close to the original as
    possible).

This module has ONE job: drive the browser and produce .xls files on disk,
one per (meter, month). It never sees the FastAPI layer.
"""
from __future__ import annotations

import calendar
import logging
import os
import time
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from app.core.config import settings

log = logging.getLogger("amr.scraper")

BASE_URL = settings.AMR_BASE_URL
LOGIN_URL = f"{BASE_URL}/AMRWEB/MainCust.aspx"
SEL_PERIOD_URL = f"{BASE_URL}/AMRWEB/selPeriodProfile.aspx"


class ScraperError(Exception):
    """Raised for any unrecoverable scraper failure (bad login, etc)."""


class LoginFailedError(ScraperError):
    pass


@dataclass
class MeterOption:
    value: str
    text: str


def _random_delay(mn: float, mx: float) -> None:
    time.sleep(random.uniform(mn, mx))


def generate_month_ranges(start_date: str, end_date: str) -> list[tuple[str, str, str]]:
    """
    start_date / end_date are exact "YYYY-MM-DD" strings (day precision).
    Internally still chunks into one request per calendar month - the AMR
    site appears to have a practical limit on how much 15-min data it will
    return per request - but the FIRST and LAST chunks are clamped to the
    exact requested day, matching the original script's behavior. Returns
    a list of (label, date_from_ddmmyyyy, date_to_ddmmyyyy).
    """
    s = datetime.strptime(start_date, "%Y-%m-%d").date()
    e = datetime.strptime(end_date, "%Y-%m-%d").date()
    ranges = []
    cur = s.replace(day=1)
    while cur <= e:
        last_day = calendar.monthrange(cur.year, cur.month)[1]
        month_end = cur.replace(day=last_day)
        chunk_start = max(s, cur)
        chunk_end = min(e, month_end)
        label = chunk_start.strftime("%d/%m/%Y") if (chunk_start.day != 1 or chunk_end != month_end) \
            else cur.strftime("%m/%Y")
        ranges.append((
            label,
            chunk_start.strftime("%d/%m/%Y"),
            chunk_end.strftime("%d/%m/%Y"),
        ))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1, day=1)
        else:
            cur = cur.replace(month=cur.month + 1, day=1)
    return ranges


def _dump_html(driver, path: Path) -> None:
    try:
        path.write_text(driver.page_source, encoding="utf-8")
    except Exception:
        log.warning("could not dump debug html to %s", path)


def setup_driver(download_dir: str) -> webdriver.Chrome:
    chrome_opts = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_setting_values.popups": 1,
    }
    chrome_opts.add_experimental_option("prefs", prefs)
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--window-size=1280,900")
    chrome_opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    chrome_opts.binary_location = settings.CHROME_BINARY

    service = Service(settings.CHROMEDRIVER_BINARY)
    driver = webdriver.Chrome(service=service, options=chrome_opts)
    driver.implicitly_wait(5)
    return driver


def amr_login(driver, username: str, password: str) -> bool:
    log.info("logging in...")
    driver.delete_all_cookies()
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 15)

    u = wait.until(EC.presence_of_element_located((By.ID, "txtUsername")))
    p = driver.find_element(By.ID, "txtPassword")
    u.clear()
    u.send_keys(username)
    p.clear()
    p.send_keys(password)

    driver.find_element(By.ID, "btnOK").click()
    _random_delay(1, 2)

    if "ยินดีต้อนรับ" in driver.page_source or "ออกจากระบบ" in driver.page_source:
        return True
    if "MainCust.aspx" not in driver.current_url:
        return True
    return False


def get_meter_info(driver, cust_code: str) -> dict:
    driver.get(f"{SEL_PERIOD_URL}?CustCode={cust_code}")
    wait = WebDriverWait(driver, 10)
    _random_delay(0.5, 1)

    meters: list[MeterOption] = []
    try:
        ddl = wait.until(EC.presence_of_element_located((By.ID, "ddlMeter")))
        for opt in ddl.find_elements(By.TAG_NAME, "option"):
            v = opt.get_attribute("value")
            t = opt.text.strip()
            if v:
                meters.append(MeterOption(value=v, text=t))
    except TimeoutException:
        pass

    custid = ""
    try:
        custid = driver.find_element(By.ID, "hdnId").get_attribute("value") or ""
    except Exception:
        pass
    if not custid:
        try:
            for h in driver.find_elements(By.CSS_SELECTOR, "input[type='hidden']"):
                name = (h.get_attribute("name") or "").lower()
                val = (h.get_attribute("value") or "").strip()
                if ("custid" in name or name == "id") and val and val != "0":
                    custid = val
                    break
        except Exception:
            pass

    return {"custid": custid, "meter_options": meters}


def wait_for_download(download_dir: str, timeout: int) -> Optional[str]:
    end_time = time.time() + timeout
    while time.time() < end_time:
        files = [f for f in os.listdir(download_dir) if f.lower().endswith((".xls", ".xlsx", ".zip"))]
        downloading = [f for f in os.listdir(download_dir) if f.endswith(".crdownload")]
        if files and not downloading:
            latest = max(files, key=lambda f: os.path.getmtime(os.path.join(download_dir, f)))
            return os.path.join(download_dir, latest)
        time.sleep(1)
    return None


def hide_overlays(driver) -> None:
    driver.execute_script("""
        ['divProgress','divLoading','divOverlay','UpdateProgress1'].forEach(function(id){
            var el = document.getElementById(id);
            if (el) {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                el.style.pointerEvents = 'none';
            }
        });
        document.querySelectorAll('div').forEach(function(el){
            var s = window.getComputedStyle(el);
            if (parseInt(s.zIndex) > 10 &&
                (s.position === 'fixed' || s.position === 'absolute') &&
                s.display !== 'none') {
                el.style.display = 'none';
            }
        });
    """)


def _fill_form(driver, meter_value: str, date_from: str, date_to: str) -> None:
    wait = WebDriverWait(driver, 10)
    try:
        ddl_meter = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlMeter"))))
        ddl_meter.select_by_value(meter_value)
        _random_delay(0.2, 0.3)
    except Exception as e:
        log.warning("could not select meter: %s", e)

    try:
        driver.find_element(By.ID, "rdo15minute").click()
        _random_delay(0.1, 0.2)
    except Exception:
        pass

    try:
        driver.execute_script(f"document.getElementById('txtDateFr').value = '{date_from}'")
        driver.execute_script(f"document.getElementById('txtDateTo').value = '{date_to}'")
        driver.execute_script("document.getElementById('txtDateFr').dispatchEvent(new Event('change'))")
        driver.execute_script("document.getElementById('txtDateTo').dispatchEvent(new Event('change'))")
        _random_delay(0.2, 0.3)
    except Exception as e:
        log.warning("could not set dates: %s", e)

    try:
        Select(driver.find_element(By.ID, "ddlReport")).select_by_value("kWh")
        _random_delay(0.1, 0.2)
    except Exception:
        pass

    try:
        driver.find_element(By.ID, "rdoData").click()
        _random_delay(0.1, 0.2)
    except Exception:
        pass


def handle_popup(driver, main_handle, cust_code, meter_value, date_from, date_to,
                  download_dir: str, debug_dir: Path, retry_login: Callable[[], bool]) -> Optional[str]:
    popup_handle = None
    for handle in driver.window_handles:
        if handle != main_handle:
            popup_handle = handle
            break
    if not popup_handle:
        return None

    driver.switch_to.window(popup_handle)
    popup_wait = WebDriverWait(driver, settings.POPUP_TIMEOUT_SECONDS)
    try:
        popup_wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    except Exception:
        pass
    _random_delay(0.5, 1)

    cur_url = driver.current_url.lower()
    if "login" in cur_url or "maincust" in cur_url:
        try:
            driver.close()
        except Exception:
            pass
        driver.switch_to.window(main_handle)
        if retry_login():
            driver.get(f"{SEL_PERIOD_URL}?CustCode={cust_code}")
            _random_delay(1, 2)
            _fill_form(driver, meter_value, date_from, date_to)
            driver.find_element(By.ID, "btnSubmit").click()
            _random_delay(5, 8)
            return handle_popup(driver, main_handle, cust_code, meter_value, date_from, date_to,
                                 download_dir, debug_dir, retry_login)
        return None

    hide_overlays(driver)
    _random_delay(0.3, 0.5)

    try:
        has_rdo = driver.execute_script("return !!document.getElementById('rdoExcel');")
        has_btn = driver.execute_script("return !!document.getElementById('btnSubmit');")
        if has_rdo and has_btn:
            driver.execute_script("document.getElementById('rdoExcel').checked = true;")
            _random_delay(0.2, 0.3)
            hide_overlays(driver)
            popup_wait.until(EC.element_to_be_clickable((By.ID, "btnSubmit")))
            driver.execute_script("document.getElementById('btnSubmit').click();")
            _random_delay(2, 3)
            downloaded = wait_for_download(download_dir, settings.DOWNLOAD_TIMEOUT_SECONDS)
            if downloaded:
                try:
                    driver.close()
                except Exception:
                    pass
                driver.switch_to.window(main_handle)
                return downloaded
    except Exception as e:
        log.warning("popup method 1 failed: %s", e)

    downloaded = None
    try:
        hide_overlays(driver)
        rdo = driver.find_element(By.ID, "rdoExcel")
        driver.execute_script("arguments[0].click();", rdo)
        _random_delay(0.2, 0.3)
        hide_overlays(driver)
        btn = driver.find_element(By.ID, "btnSubmit")
        driver.execute_script("arguments[0].click();", btn)
        _random_delay(2, 3)
        downloaded = wait_for_download(download_dir, settings.DOWNLOAD_TIMEOUT_SECONDS)
    except Exception as e:
        log.error("popup method 2 failed: %s", e)
        _dump_html(driver, debug_dir / f"popup_fail_{meter_value}_{date_from.replace('/', '')}.html")

    try:
        driver.close()
    except Exception:
        pass
    driver.switch_to.window(main_handle)
    return downloaded


def download_month(driver, cust_code, meter_value, date_from, date_to,
                    download_dir: str, debug_dir: Path, retry_login: Callable[[], bool]) -> Optional[str]:
    main_handle = driver.current_window_handle
    initial_handles = set(driver.window_handles)

    driver.get(f"{SEL_PERIOD_URL}?CustCode={cust_code}")
    _random_delay(0.8, 1.2)
    _fill_form(driver, meter_value, date_from, date_to)
    _random_delay(0.2, 0.3)

    try:
        btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "btnSubmit")))
        btn.click()
    except Exception as e:
        log.error("could not click submit: %s", e)
        return None

    popup_opened = False
    for _ in range(40):
        time.sleep(0.25)
        if set(driver.window_handles) - initial_handles:
            popup_opened = True
            break

    if popup_opened:
        return handle_popup(driver, main_handle, cust_code, meter_value, date_from, date_to,
                             download_dir, debug_dir, retry_login)

    if "showPeriodProfile" in driver.current_url:
        _random_delay(1, 2)
        # Original script's fallback path for direct-download pages.
        DOWNLOAD_KEYWORDS = ["excel", "download", "ดาวน์โหลด", "ส่งออก", "export"]
        try:
            for b in driver.find_elements(By.TAG_NAME, "input"):
                v = (b.get_attribute("value") or "")
                if any(x in v.lower() for x in DOWNLOAD_KEYWORDS):
                    handles_before = set(driver.window_handles)
                    b.click()
                    for _ in range(20):
                        time.sleep(0.25)
                        if set(driver.window_handles) - handles_before:
                            return handle_popup(driver, main_handle, cust_code, meter_value,
                                                 date_from, date_to, download_dir, debug_dir, retry_login)
                    return wait_for_download(download_dir, 60)
        except Exception as e:
            log.warning("show-page fallback failed: %s", e)
        return None

    _dump_html(driver, debug_dir / f"no_popup_{meter_value}_{date_from.replace('/', '')}.html")
    return None


class AmrScraper:
    """
    Drives one full scrape for one job: login, discover meters (optional),
    then loop over months for the selected meter(s), downloading one .xls
    per (meter, month) into job.work_dir/xls/.

    on_progress(completed, total, message) is called after every month.
    """

    def __init__(self, work_dir: Path, on_progress: Callable[[int, int, str], None]):
        self.work_dir = work_dir
        self.xls_dir = work_dir / "xls"
        self.debug_dir = work_dir / "debug"
        self.debug_dir.mkdir(exist_ok=True)
        self.on_progress = on_progress
        self.driver: Optional[webdriver.Chrome] = None
        self._username = ""
        self._password = ""

    def _retry_login(self) -> bool:
        return amr_login(self.driver, self._username, self._password)

    def open_and_login(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self.driver = setup_driver(str(self.xls_dir))
        if not amr_login(self.driver, username, password):
            raise LoginFailedError("เข้าสู่ระบบไม่สำเร็จ กรุณาตรวจสอบ username/password")

    def discover_meters(self, cust_code: str) -> list[MeterOption]:
        info = get_meter_info(self.driver, cust_code)
        return info["meter_options"]

    def run_months(self, cust_code: str, meter_values: list[str],
                    month_ranges: list[tuple[str, str, str]]) -> list[dict]:
        """
        Returns a list of dicts: {label, meter_value, success, xls_path, error}
        one per (meter, month) combination, in order.
        """
        results = []
        tasks = [(mv, label, df, dt) for mv in meter_values for (label, df, dt) in month_ranges]
        total = len(tasks)

        for idx, (meter_value, label, date_from, date_to) in enumerate(tasks, 1):
            try:
                path = download_month(
                    self.driver, cust_code, meter_value, date_from, date_to,
                    str(self.xls_dir), self.debug_dir, self._retry_login,
                )
                if path:
                    results.append({
                        "label": label, "meter_value": meter_value,
                        "success": True, "xls_path": path, "error": None,
                    })
                    self.on_progress(idx, total, f"ดาวน์โหลดสำเร็จ: {label}")
                else:
                    results.append({
                        "label": label, "meter_value": meter_value,
                        "success": False, "xls_path": None,
                        "error": "ไม่พบไฟล์ดาวน์โหลดหลังรอครบเวลา",
                    })
                    self.on_progress(idx, total, f"ดาวน์โหลดไม่สำเร็จ: {label}")
            except Exception as e:
                log.exception("error downloading %s", label)
                results.append({
                    "label": label, "meter_value": meter_value,
                    "success": False, "xls_path": None, "error": str(e),
                })
                self.on_progress(idx, total, f"เกิดข้อผิดพลาด: {label}")
            _random_delay(0.5, 1)

        return results

    def close(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
