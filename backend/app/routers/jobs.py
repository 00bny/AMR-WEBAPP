"""
Jobs router - every endpoint the frontend talks to.

Flow:
  POST   /jobs                       -> create job, start login+meter discovery
  GET    /jobs/{id}                  -> poll status/progress (called every 1-2s by the frontend)
  POST   /jobs/{id}/meters           -> user picks which meter(s) to scrape (only if >1 found)
  POST   /jobs/{id}/merge            -> merge all successfully-converted xlsx files
  POST   /jobs/{id}/charts           -> generate the chosen chart categories
  GET    /jobs/{id}/files            -> list what's available to download
  GET    /jobs/{id}/charts/{category}/{filename} -> serve one chart image (for inline preview)
  POST   /jobs/{id}/download         -> build a zip of the selected items and stream it back
  DELETE /jobs/{id}                  -> user is done, delete everything now instead of waiting for TTL
"""
from __future__ import annotations

import logging
import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.jobs.models import JobStatus
from app.jobs.runner import chart_task, discover_meters_task, merge_task, start_scrape_task
from app.jobs.store import job_store
from app.routers.schemas import ChartRequest, FileSelection, SelectMetersRequest, StartJobRequest

log = logging.getLogger("amr.router")
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _validate_date_range(start: str, end: str) -> None:
    if start > end:
        raise HTTPException(400, "วันที่เริ่มต้นต้องมาก่อนวันที่สิ้นสุด")


@router.post("")
async def create_job(req: StartJobRequest, background_tasks: BackgroundTasks):
    _validate_date_range(req.start_date, req.end_date)

    job = await job_store.create()
    job.username = req.username
    job.password = req.password
    job.start_date = req.start_date
    job.end_date = req.end_date

    background_tasks.add_task(discover_meters_task, job)
    return {"job_id": job.job_id}


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = await job_store.get(job_id)
    if not job:
        raise HTTPException(404, "ไม่พบงานนี้ อาจถูกลบไปแล้วเนื่องจากหมดเวลา")
    return job.public_dict()


@router.post("/{job_id}/meters")
async def select_meters(job_id: str, req: SelectMetersRequest, background_tasks: BackgroundTasks):
    job = await job_store.get(job_id)
    if not job:
        raise HTTPException(404, "ไม่พบงานนี้")
    if not job.awaiting_meter_choice:
        raise HTTPException(400, "งานนี้ไม่ได้อยู่ในขั้นตอนเลือกมิเตอร์")
    if not req.meter_values:
        raise HTTPException(400, "กรุณาเลือกมิเตอร์อย่างน้อย 1 ตัว")

    job.selected_meters = req.meter_values
    background_tasks.add_task(start_scrape_task, job)
    return {"ok": True}


@router.post("/{job_id}/merge")
async def merge(job_id: str, background_tasks: BackgroundTasks):
    job = await job_store.get(job_id)
    if not job:
        raise HTTPException(404, "ไม่พบงานนี้")
    if job.status != JobStatus.READY_TO_MERGE:
        raise HTTPException(400, f"งานนี้ยังไม่พร้อมรวมไฟล์ (สถานะปัจจุบัน: {job.status.value})")

    background_tasks.add_task(merge_task, job)
    return {"ok": True}


@router.post("/{job_id}/charts")
async def make_charts(job_id: str, req: ChartRequest, background_tasks: BackgroundTasks):
    job = await job_store.get(job_id)
    if not job:
        raise HTTPException(404, "ไม่พบงานนี้")
    if job.status not in (JobStatus.READY_TO_CHART, JobStatus.DONE):
        raise HTTPException(400, f"งานนี้ยังไม่พร้อมสร้างกราฟ (สถานะปัจจุบัน: {job.status.value})")
    if not req.categories:
        raise HTTPException(400, "กรุณาเลือกหมวดหมู่กราฟอย่างน้อย 1 หมวด")

    background_tasks.add_task(chart_task, job, req.categories)
    return {"ok": True}


@router.get("/{job_id}/files")
async def list_files(job_id: str):
    job = await job_store.get(job_id)
    if not job:
        raise HTTPException(404, "ไม่พบงานนี้")

    chart_files = {
        cat: filenames.split(",") if filenames else []
        for cat, filenames in job.chart_paths.items()
    }

    return {
        "xls_count": sum(1 for m in job.months if m.xls_path),
        "xlsx_count": sum(1 for m in job.months if m.xlsx_path),
        "has_merged": job.merged_xlsx_path is not None,
        "chart_categories": chart_files,
    }


@router.get("/{job_id}/charts/{filename}")
async def get_chart_image(job_id: str, filename: str):
    job = await job_store.get(job_id)
    if not job:
        raise HTTPException(404, "ไม่พบงานนี้")
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "ชื่อไฟล์ไม่ถูกต้อง")
    path = job.work_dir / "charts" / filename
    if not path.is_file():
        raise HTTPException(404, "ไม่พบไฟล์ภาพนี้")
    return FileResponse(path, media_type="image/png")


@router.post("/{job_id}/download")
async def download_zip(job_id: str, selection: FileSelection):
    job = await job_store.get(job_id)
    if not job:
        raise HTTPException(404, "ไม่พบงานนี้")

    def iter_zip():
        import io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            if selection.include_xls:
                for m in job.months:
                    if m.xls_path and Path(m.xls_path).exists():
                        zf.write(m.xls_path, arcname=f"xls/{Path(m.xls_path).name}")
            if selection.include_xlsx:
                for m in job.months:
                    if m.xlsx_path and Path(m.xlsx_path).exists():
                        zf.write(m.xlsx_path, arcname=f"xlsx/{Path(m.xlsx_path).name}")
            if selection.include_merged and job.merged_xlsx_path and Path(job.merged_xlsx_path).exists():
                zf.write(job.merged_xlsx_path, arcname=Path(job.merged_xlsx_path).name)
            if selection.chart_categories:
                charts_dir = job.work_dir / "charts"
                if charts_dir.exists():
                    for png in charts_dir.glob("*.png"):
                        zf.write(png, arcname=f"charts/{png.name}")
        buf.seek(0)
        yield from buf

    return StreamingResponse(
        iter_zip(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="amr_data_{job_id}.zip"'},
    )


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    await job_store.delete(job_id)
    return {"ok": True}
