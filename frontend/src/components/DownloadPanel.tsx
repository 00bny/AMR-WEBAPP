"use client";

import { useState } from "react";
import { CHART_CATEGORIES } from "@/types/job";

interface DownloadPanelProps {
  hasMerged: boolean;
  readyChartCategories: string[];
  onDownload: (selection: {
    include_xls: boolean;
    include_xlsx: boolean;
    include_merged: boolean;
    chart_categories: string[];
  }) => void;
  downloading?: boolean;
}

export function DownloadPanel({
  hasMerged,
  readyChartCategories,
  onDownload,
  downloading,
}: DownloadPanelProps) {
  const [includeXls, setIncludeXls] = useState(false);
  const [includeXlsx, setIncludeXlsx] = useState(false);
  const [includeMerged, setIncludeMerged] = useState(true);
  const [chartCats, setChartCats] = useState<Set<string>>(
    new Set(readyChartCategories)
  );

  const toggleChartCat = (id: string) => {
    setChartCats((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    setIncludeXls(true);
    setIncludeXlsx(true);
    setIncludeMerged(true);
    setChartCats(new Set(readyChartCategories));
  };

  const nothingSelected =
    !includeXls && !includeXlsx && !includeMerged && chartCats.size === 0;

  return (
    <div className="rounded-xl border border-base-700 bg-base-900 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium text-base-100">เลือกไฟล์ที่ต้องการบันทึก</h3>
        <button
          onClick={selectAll}
          className="text-xs font-medium text-signal-400 hover:text-signal-300"
        >
          เลือกทั้งหมด
        </button>
      </div>

      <div className="flex flex-col gap-2">
        <label className="flex items-center gap-3 rounded-lg border border-base-600 bg-base-800 px-3 py-2.5">
          <input
            type="checkbox"
            checked={includeMerged}
            disabled={!hasMerged}
            onChange={(e) => setIncludeMerged(e.target.checked)}
            className="h-4 w-4 accent-signal-500"
          />
          <span className="text-sm text-base-100">
            ไฟล์รวมทุกเดือน (combined_monthly.xlsx)
          </span>
        </label>

        <label className="flex items-center gap-3 rounded-lg border border-base-600 bg-base-800 px-3 py-2.5">
          <input
            type="checkbox"
            checked={includeXlsx}
            onChange={(e) => setIncludeXlsx(e.target.checked)}
            className="h-4 w-4 accent-signal-500"
          />
          <span className="text-sm text-base-100">ไฟล์ .xlsx แยกตามเดือน</span>
        </label>

        <label className="flex items-center gap-3 rounded-lg border border-base-600 bg-base-800 px-3 py-2.5">
          <input
            type="checkbox"
            checked={includeXls}
            onChange={(e) => setIncludeXls(e.target.checked)}
            className="h-4 w-4 accent-signal-500"
          />
          <span className="text-sm text-base-100">ไฟล์ .xls ต้นฉบับ</span>
        </label>

        {readyChartCategories.length > 0 && (
          <div className="rounded-lg border border-base-600 bg-base-800 px-3 py-2.5">
            <p className="mb-2 text-sm text-base-100">รูปกราฟ</p>
            <div className="flex flex-col gap-1.5">
              {readyChartCategories.map((id) => {
                const cat = CHART_CATEGORIES.find((c) => c.id === id);
                return (
                  <label key={id} className="flex items-center gap-2.5">
                    <input
                      type="checkbox"
                      checked={chartCats.has(id)}
                      onChange={() => toggleChartCat(id)}
                      className="h-3.5 w-3.5 accent-signal-500"
                    />
                    <span className="text-xs text-base-300">
                      {cat?.label || id}
                    </span>
                  </label>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <button
        onClick={() =>
          onDownload({
            include_xls: includeXls,
            include_xlsx: includeXlsx,
            include_merged: includeMerged,
            chart_categories: Array.from(chartCats),
          })
        }
        disabled={nothingSelected || downloading}
        className="mt-4 w-full rounded-lg bg-signal-500 px-4 py-2.5 text-sm font-medium text-base-950 transition-colors hover:bg-signal-400 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {downloading ? "กำลังเตรียมไฟล์..." : "ดาวน์โหลด (.zip)"}
      </button>
    </div>
  );
}
