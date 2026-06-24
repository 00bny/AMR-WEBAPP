"""
Central configuration, read from environment variables (set in Render's
dashboard for production, or a local .env for development).
"""
import os
from pathlib import Path


class Settings:
    # --- AMR site ---
    AMR_BASE_URL: str = os.getenv("AMR_BASE_URL", "https://www.amr.pea.co.th")

    # --- Concurrency ---
    # How many Selenium scrape jobs may run at the same time. Each one opens
    # a real headless Chrome process (~150-300MB RAM), so keep this low on
    # Render's free tier (512MB RAM total).
    MAX_CONCURRENT_SCRAPES: int = int(os.getenv("MAX_CONCURRENT_SCRAPES", "1"))

    # --- Storage / cleanup ---
    TEMP_ROOT: str = os.getenv("TEMP_ROOT", str(Path("/tmp/amr_jobs")))
    # Delete a finished/failed job's folder this many seconds after it
    # finished, even if nobody downloaded the result.
    JOB_TTL_AFTER_DONE_SECONDS: int = int(os.getenv("JOB_TTL_AFTER_DONE_SECONDS", str(30 * 60)))
    # Hard cap: delete any job (finished or not) after this long, in case a
    # worker crashed and left it stuck.
    JOB_TTL_MAX_SECONDS: int = int(os.getenv("JOB_TTL_MAX_SECONDS", str(2 * 60 * 60)))
    CLEANUP_SWEEP_SECONDS: int = int(os.getenv("CLEANUP_SWEEP_SECONDS", "300"))

    # --- CORS ---
    ALLOWED_ORIGINS: list[str] = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000"
    ).split(",")

    # --- Selenium ---
    CHROME_BINARY: str = os.getenv("CHROME_BINARY", "/usr/bin/chromium")
    CHROMEDRIVER_BINARY: str = os.getenv("CHROMEDRIVER_BINARY", "/usr/bin/chromedriver")
    DOWNLOAD_TIMEOUT_SECONDS: int = int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "120"))
    POPUP_TIMEOUT_SECONDS: int = int(os.getenv("POPUP_TIMEOUT_SECONDS", "30"))


settings = Settings()
Path(settings.TEMP_ROOT).mkdir(parents=True, exist_ok=True)
