"""
Job state models.

A "job" represents one user's end-to-end run: login -> download months ->
convert -> merge -> chart -> zip. Everything lives in memory (a dict keyed
by job_id) and on a temp folder on disk. Nothing is written to a database
and credentials are never persisted to disk or logs.
"""
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    LOGGING_IN = "logging_in"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    READY_TO_MERGE = "ready_to_merge"
    MERGING = "merging"
    READY_TO_CHART = "ready_to_chart"
    CHARTING = "charting"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MeterOption:
    value: str
    text: str


@dataclass
class MonthResult:
    label: str          # e.g. "06/2025"
    date_from: str       # dd/mm/yyyy
    date_to: str
    success: bool = False
    xls_path: Optional[str] = None
    xlsx_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class JobState:
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: JobStatus = JobStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # progress reporting (safe to expose to the client)
    progress_pct: float = 0.0
    current_step: str = "รอในคิว..."
    total_months: int = 0
    completed_months: int = 0

    # inputs (credentials live here ONLY in memory, cleared on completion/failure)
    username: Optional[str] = None
    password: Optional[str] = None
    start_date: Optional[str] = None  # "2025-06-15"
    end_date: Optional[str] = None    # "2026-05-20"
    selected_meters: list[str] = field(default_factory=list)

    # discovered meters (after login) the user can choose from
    available_meters: list[MeterOption] = field(default_factory=list)
    awaiting_meter_choice: bool = False

    # results
    months: list[MonthResult] = field(default_factory=list)
    merged_xlsx_path: Optional[str] = None
    chart_paths: dict[str, str] = field(default_factory=dict)  # category -> png path

    error_message: Optional[str] = None
    work_dir: Optional[Path] = None

    def clear_credentials(self) -> None:
        self.username = None
        self.password = None

    def touch(self) -> None:
        self.updated_at = time.time()

    def public_dict(self) -> dict:
        """Only fields safe to send to the frontend - never username/password."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress_pct": round(self.progress_pct, 1),
            "current_step": self.current_step,
            "total_months": self.total_months,
            "completed_months": self.completed_months,
            "available_meters": [m.__dict__ for m in self.available_meters],
            "awaiting_meter_choice": self.awaiting_meter_choice,
            "months": [
                {
                    "label": m.label,
                    "success": m.success,
                    "error": m.error,
                }
                for m in self.months
            ],
            "has_merged_file": self.merged_xlsx_path is not None,
            "chart_categories_ready": list(self.chart_paths.keys()),
            "error_message": self.error_message,
        }
