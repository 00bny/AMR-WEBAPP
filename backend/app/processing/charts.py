"""
Chart generation - ported from Load_Profile_Analysis.ipynb.

Each notebook cell becomes one function here, keyed by a `category` id the
frontend uses for its checkboxes. Every function takes the merged dataframe
and an output directory, and returns the list of PNG paths it produced
(some categories produce one image, others - like "by day of week" - produce
several).

Matplotlib calls are identical to the notebook (same colors, same boxplot/
violin styling) - only the file I/O changed (job-specific output folder
instead of a hardcoded "png/" folder).
"""
from __future__ import annotations

import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless rendering - no display server on the server
import matplotlib.pyplot as plt
import pandas as pd

log = logging.getLogger("amr.charts")

matplotlib.rcParams["figure.figsize"] = (14, 6)
matplotlib.rcParams["font.family"] = "DejaVu Sans"

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS_ORDER = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]

ORANGE = "#FF4800"

CATEGORY_LABELS = {
    "dotplot_all": "Dotplot ภาพรวมทั้งหมด",
    "boxplot_violin_all": "Boxplot + Violin ภาพรวมทั้งหมด",
    "by_day_of_week": "Boxplot แยกตามวันในสัปดาห์",
    "by_month": "Boxplot แยกตามเดือน (เปรียบเทียบรายเดือน)",
    "by_month_detail": "Boxplot แยกตามเดือน x ช่วงเวลา (ละเอียด)",
    "weekdays_only": "Boxplot เฉพาะวันธรรมดา แยกตามเดือน",
    "weekend_only": "Boxplot เฉพาะเสาร์-อาทิตย์",
}


def _box_style():
    return dict(
        patch_artist=True,
        boxprops=dict(facecolor=ORANGE, alpha=0.7),
        medianprops=dict(color="black", linewidth=2),
        whiskerprops=dict(color="gray"),
        capprops=dict(color="gray"),
        flierprops=dict(marker="o", color=ORANGE, alpha=0.3, markersize=3),
    )


def chart_dotplot_all(df: pd.DataFrame, out_dir: Path) -> list[str]:
    fig, ax = plt.subplots(figsize=(14, 6))
    time_groups = sorted(df["TimeGroup"].dropna().unique())
    x_pos = {tg: i + 1 for i, tg in enumerate(time_groups)}

    for tg in time_groups:
        vals = df[df["TimeGroup"] == tg]["kW"].values
        ax.scatter([x_pos[tg]] * len(vals), vals, color=ORANGE, alpha=0.3, s=5)

    ax.set_xticks(range(1, len(time_groups) + 1))
    ax.set_xticklabels(time_groups, rotation=45, ha="right")
    ax.set_xlabel("Time Period")
    ax.set_ylabel("Energy Consumption (kW)")
    ax.set_title("Energy Consumption — Dot Distribution")
    plt.tight_layout()
    path = out_dir / "01_dotplot_all.png"
    plt.savefig(path, dpi=150)
    plt.close(fig)
    return [str(path)]


def chart_boxplot_violin_all(df: pd.DataFrame, out_dir: Path) -> list[str]:
    fig, ax = plt.subplots(figsize=(14, 6))
    time_groups = sorted(df["TimeGroup"].dropna().unique())
    data_by_tg = [df[df["TimeGroup"] == tg]["kW"].dropna().values for tg in time_groups]

    parts = ax.violinplot(data_by_tg, positions=range(1, len(time_groups) + 1),
                           showmeans=False, showextrema=False)
    for pc in parts["bodies"]:
        pc.set_facecolor("royalblue")
        pc.set_alpha(0.25)

    ax.boxplot(data_by_tg, positions=range(1, len(time_groups) + 1), **_box_style())

    ax.set_xticks(range(1, len(time_groups) + 1))
    ax.set_xticklabels(time_groups, rotation=45, ha="right")
    ax.set_xlabel("Time Period")
    ax.set_ylabel("Energy Consumption (kW)")
    ax.set_title("Energy Consumption — Boxplot + Violin (All Data)")
    plt.tight_layout()
    path = out_dir / "02_boxplot_violin_all.png"
    plt.savefig(path, dpi=150)
    plt.close(fig)
    return [str(path)]


def chart_by_day_of_week(df: pd.DataFrame, out_dir: Path) -> list[str]:
    time_groups = sorted(df["TimeGroup"].dropna().unique())
    paths = []
    for idx, day in enumerate(DAYS_OF_WEEK, start=3):
        day_data = df[df["Days"] == day]
        if day_data.empty:
            continue
        data_by_tg = [day_data[day_data["TimeGroup"] == tg]["kW"].dropna().values for tg in time_groups]
        valid = [(tg, d) for tg, d in zip(time_groups, data_by_tg) if len(d) > 0]
        if not valid:
            continue
        labels, groups = zip(*valid)

        fig, ax = plt.subplots(figsize=(14, 6))
        ax.boxplot(list(groups), **_box_style())
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_xlabel("Time Period")
        ax.set_ylabel("Energy Consumption (kW)")
        ax.set_title(f"Energy Consumption for {day}")
        plt.tight_layout()
        path = out_dir / f"{idx:02d}_load_profile_{day}.png"
        plt.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(str(path))
    return paths


def chart_by_month(df: pd.DataFrame, out_dir: Path) -> list[str]:
    months_in_data = [m for m in MONTHS_ORDER if m in df["Month"].unique()]
    kw_monthly = [df[df["Month"] == m]["kW"].dropna().values for m in months_in_data]
    if not months_in_data:
        return []

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.boxplot(kw_monthly, **_box_style())
    ax.set_xticks(range(1, len(months_in_data) + 1))
    ax.set_xticklabels(months_in_data, rotation=45, ha="right")
    ax.set_xlabel("Month")
    ax.set_ylabel("Energy Consumption (kW)")
    ax.set_title("Energy Consumption — Monthly Comparison")
    plt.tight_layout()
    path = out_dir / "10_boxplot_monthly.png"
    plt.savefig(path, dpi=150)
    plt.close(fig)
    return [str(path)]


def chart_by_month_detail(df: pd.DataFrame, out_dir: Path) -> list[str]:
    time_groups = sorted(df["TimeGroup"].dropna().unique())
    paths = []
    for idx, month in enumerate(MONTHS_ORDER, start=11):
        month_data = df[df["Month"] == month]
        if month_data.empty:
            continue
        data_by_tg = [month_data[month_data["TimeGroup"] == tg]["kW"].dropna().values for tg in time_groups]
        valid = [(tg, d) for tg, d in zip(time_groups, data_by_tg) if len(d) > 0]
        if not valid:
            continue
        labels, groups = zip(*valid)

        fig, ax = plt.subplots(figsize=(14, 6))
        ax.boxplot(list(groups), **_box_style())
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_xlabel("Time Period")
        ax.set_ylabel("Energy Consumption (kW)")
        ax.set_title(f"Energy Consumption for {month}")
        plt.tight_layout()
        path = out_dir / f"{idx:02d}_load_profile_{month}.png"
        plt.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(str(path))
    return paths


def chart_weekdays_only(df: pd.DataFrame, out_dir: Path) -> list[str]:
    df_weekday = df[~df["Days"].isin(["Saturday", "Sunday"])]
    time_groups = sorted(df_weekday["TimeGroup"].dropna().unique())
    paths = []
    for idx, month in enumerate(MONTHS_ORDER, start=23):
        month_data = df_weekday[df_weekday["Month"] == month]
        if month_data.empty:
            continue
        data_by_tg = [month_data[month_data["TimeGroup"] == tg]["kW"].dropna().values for tg in time_groups]
        valid = [(tg, d) for tg, d in zip(time_groups, data_by_tg) if len(d) > 0]
        if not valid:
            continue
        labels, groups = zip(*valid)

        fig, ax = plt.subplots(figsize=(14, 6))
        ax.boxplot(list(groups), **_box_style())
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_xlabel("Time Period")
        ax.set_ylabel("Energy Consumption (kW)")
        ax.set_title(f"Energy Consumption for {month} (Weekdays Only)")
        plt.tight_layout()
        path = out_dir / f"{idx:02d}_load_profile_{month}_weekdays.png"
        plt.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(str(path))
    return paths


def chart_weekend_only(df: pd.DataFrame, out_dir: Path) -> list[str]:
    df_weekend = df[df["Days"].isin(["Saturday", "Sunday"])]
    time_groups = sorted(df_weekend["TimeGroup"].dropna().unique())
    data_by_tg = [df_weekend[df_weekend["TimeGroup"] == tg]["kW"].dropna().values for tg in time_groups]
    valid = [(tg, d) for tg, d in zip(time_groups, data_by_tg) if len(d) > 0]
    if not valid:
        return []
    labels, groups = zip(*valid)

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.boxplot(list(groups), **_box_style())
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_xlabel("Time Period")
    ax.set_ylabel("Energy Consumption (kW)")
    ax.set_title("Energy Consumption — Saturday & Sunday")
    plt.tight_layout()
    path = out_dir / "35_load_profile_saturday_sunday.png"
    plt.savefig(path, dpi=150)
    plt.close(fig)
    return [str(path)]


CATEGORY_FUNCS = {
    "dotplot_all": chart_dotplot_all,
    "boxplot_violin_all": chart_boxplot_violin_all,
    "by_day_of_week": chart_by_day_of_week,
    "by_month": chart_by_month,
    "by_month_detail": chart_by_month_detail,
    "weekdays_only": chart_weekdays_only,
    "weekend_only": chart_weekend_only,
}


def generate_charts(merged_xlsx_path: str, categories: list[str], out_dir: Path) -> dict[str, list[str]]:
    """Loads the merged file once, then runs each requested category.
    Returns {category: [png_paths]}."""
    df = pd.read_excel(merged_xlsx_path, sheet_name="Sheet1")
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[str]] = {}
    for cat in categories:
        func = CATEGORY_FUNCS.get(cat)
        if not func:
            log.warning("unknown chart category requested: %s", cat)
            continue
        try:
            results[cat] = func(df, out_dir)
        except Exception:
            log.exception("chart category %s failed", cat)
            results[cat] = []
    return results
