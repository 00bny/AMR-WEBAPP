"""
Job runner - the async orchestration layer that ties scraper + processing
together and updates JobState as it goes, so the frontend's polling endpoint
always has a fresh progress_pct / current_step to show.

Selenium is blocking I/O, so the actual scrape runs in a worker thread via
asyncio.to_thread - this keeps the FastAPI event loop free to answer other
requests (like other users' progress polls) while a scrape is in flight.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.jobs.models import JobState, JobStatus, MeterOption, MonthResult
from app.jobs.store import job_store
from app.processing.convert import convert_xls_to_xlsx
from app.processing.merge import merge_files
from app.processing.charts import generate_charts
from app.scraper.amr_scraper import AmrScraper, LoginFailedError, generate_month_ranges

log = logging.getLogger("amr.runner")


async def discover_meters_task(job: JobState) -> None:
    """First phase: login and report back what meters this account has, so
    the frontend can show a picker before the (slow) scrape begins."""
    job.status = JobStatus.LOGGING_IN
    job.current_step = "กำลังเข้าสู่ระบบ..."
    job.touch()

    async with job_store.scrape_semaphore:
        try:
            meters = await asyncio.to_thread(_discover_meters_blocking, job)
        except LoginFailedError as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.clear_credentials()
            job.touch()
            return
        except Exception as e:
            log.exception("meter discovery failed for job %s", job.job_id)
            job.status = JobStatus.FAILED
            job.error_message = f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}"
            job.clear_credentials()
            job.touch()
            return

    job.available_meters = meters
    if len(meters) <= 1:
        job.selected_meters = [m.value for m in meters] if meters else [job.username or ""]
        job.awaiting_meter_choice = False
        await start_scrape_task(job)
    else:
        job.awaiting_meter_choice = True
        job.status = JobStatus.LOGGING_IN
        job.current_step = "พบหลายมิเตอร์ กรุณาเลือกมิเตอร์ที่ต้องการ"
        job.touch()


def _discover_meters_blocking(job: JobState) -> list[MeterOption]:
    scraper = AmrScraper(job.work_dir, on_progress=lambda *_: None)
    try:
        scraper.open_and_login(job.username, job.password)
        meters = scraper.discover_meters(cust_code=job.username)
        return meters
    finally:
        scraper.close()


async def start_scrape_task(job: JobState) -> None:
    """Second phase: actually download every (meter, month) combination,
    converting each .xls to .xlsx as soon as it lands."""
    job.status = JobStatus.DOWNLOADING
    job.awaiting_meter_choice = False
    job.touch()

    month_ranges = generate_month_ranges(job.start_date, job.end_date)
    job.total_months = len(month_ranges) * max(1, len(job.selected_meters))
    job.completed_months = 0

    async with job_store.scrape_semaphore:
        try:
            month_results = await asyncio.to_thread(
                _scrape_and_convert_blocking, job, month_ranges
            )
        except LoginFailedError as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.clear_credentials()
            job.touch()
            return
        except Exception as e:
            log.exception("scrape failed for job %s", job.job_id)
            job.status = JobStatus.FAILED
            job.error_message = f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}"
            job.clear_credentials()
            job.touch()
            return

    job.months = month_results
    job.clear_credentials()  # done with the browser - no reason to keep these in RAM

    ok_count = sum(1 for m in month_results if m.success)
    if ok_count == 0:
        job.status = JobStatus.FAILED
        job.error_message = "ไม่สามารถดาวน์โหลดข้อมูลเดือนใดได้เลย กรุณาตรวจสอบ username/password และลองใหม่"
        job.touch()
        return

    job.status = JobStatus.READY_TO_MERGE
    job.current_step = f"ดาวน์โหลดและแปลงไฟล์เสร็จแล้ว ({ok_count}/{len(month_results)} เดือนสำเร็จ)"
    job.progress_pct = 100.0
    job.touch()


def _scrape_and_convert_blocking(job: JobState, month_ranges) -> list[MonthResult]:
    xlsx_dir = job.work_dir / "xlsx"

    def on_progress(completed: int, total: int, message: str) -> None:
        job.completed_months = completed
        job.progress_pct = (completed / total) * 90 if total else 0  # leave 10% for convert
        job.current_step = message
        job.touch()

    scraper = AmrScraper(job.work_dir, on_progress=on_progress)
    try:
        scraper.open_and_login(job.username, job.password)
        raw_results = scraper.run_months(
            cust_code=job.username,
            meter_values=job.selected_meters or [job.username],
            month_ranges=month_ranges,
        )
    finally:
        scraper.close()

    job.status = JobStatus.CONVERTING
    job.current_step = "กำลังแปลงไฟล์ .xls เป็น .xlsx ..."
    job.touch()

    results: list[MonthResult] = []
    for r in raw_results:
        mr = MonthResult(label=r["label"], date_from="", date_to="", success=r["success"])
        if r["success"] and r["xls_path"]:
            try:
                xlsx_path = convert_xls_to_xlsx(r["xls_path"], xlsx_dir)
                mr.xls_path = r["xls_path"]
                mr.xlsx_path = xlsx_path
            except Exception as e:
                log.warning("convert failed for %s: %s", r["label"], e)
                mr.success = False
                mr.error = f"แปลงไฟล์ไม่สำเร็จ: {e}"
        else:
            mr.error = r.get("error")
        results.append(mr)

    job.progress_pct = 100.0
    return results


async def merge_task(job: JobState) -> None:
    job.status = JobStatus.MERGING
    job.current_step = "กำลังรวมไฟล์ทั้งหมดเป็นไฟล์เดียว..."
    job.touch()

    xlsx_paths = [m.xlsx_path for m in job.months if m.success and m.xlsx_path]
    output_path = str(job.work_dir / "combined_monthly.xlsx")

    try:
        summary = await asyncio.to_thread(merge_files, xlsx_paths, output_path)
    except Exception as e:
        log.exception("merge failed for job %s", job.job_id)
        job.status = JobStatus.FAILED
        job.error_message = f"รวมไฟล์ไม่สำเร็จ: {e}"
        job.touch()
        return

    if not summary["merged"]:
        job.status = JobStatus.FAILED
        job.error_message = "ไม่สามารถรวมไฟล์ได้ - ไฟล์ทุกไฟล์อ่านไม่สำเร็จ"
        job.touch()
        return

    job.merged_xlsx_path = output_path
    job.status = JobStatus.READY_TO_CHART
    job.current_step = f"รวมไฟล์สำเร็จ ({summary['rows']} แถว จาก {summary['files_ok']} ไฟล์)"
    job.touch()


async def chart_task(job: JobState, categories: list[str]) -> None:
    job.status = JobStatus.CHARTING
    job.current_step = "กำลังสร้างกราฟ..."
    job.touch()

    if not job.merged_xlsx_path:
        job.status = JobStatus.FAILED
        job.error_message = "ยังไม่มีไฟล์ที่รวมแล้ว กรุณารวมไฟล์ก่อนสร้างกราฟ"
        job.touch()
        return

    charts_dir = job.work_dir / "charts"
    try:
        results = await asyncio.to_thread(generate_charts, job.merged_xlsx_path, categories, charts_dir)
    except Exception as e:
        log.exception("chart generation failed for job %s", job.job_id)
        job.status = JobStatus.FAILED
        job.error_message = f"สร้างกราฟไม่สำเร็จ: {e}"
        job.touch()
        return

    for cat, paths in results.items():
        if paths:
            # store comma-joined filenames so /files can report exactly
            # which images belong to which category (the folder is shared
            # across categories, so listing *.png alone isn't enough).
            job.chart_paths[cat] = ",".join(Path(p).name for p in paths)

    job.status = JobStatus.DONE
    job.current_step = "เสร็จสมบูรณ์"
    job.touch()
