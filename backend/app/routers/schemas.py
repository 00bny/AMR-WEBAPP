from __future__ import annotations

from pydantic import BaseModel, Field


class StartJobRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    start_date: str = Field(..., description="YYYY-MM-DD, e.g. 2025-06-15")
    end_date: str = Field(..., description="YYYY-MM-DD, e.g. 2026-05-20")


class SelectMetersRequest(BaseModel):
    meter_values: list[str]


class ChartRequest(BaseModel):
    categories: list[str]


class FileSelection(BaseModel):
    include_xls: bool = False
    include_xlsx: bool = False
    include_merged: bool = True
    chart_categories: list[str] = []
