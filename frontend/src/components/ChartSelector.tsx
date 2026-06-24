"use client";

import { useState } from "react";
import { CHART_CATEGORIES } from "@/types/job";

interface ChartSelectorProps {
  onGenerate: (categories: string[]) => void;
  generating?: boolean;
  readyCategories: string[];
}

export function ChartSelector({
  onGenerate,
  generating,
  readyCategories,
}: ChartSelectorProps) {
  const [selected, setSelected] = useState<Set<string>>(
    new Set(["dotplot_all", "boxplot_violin_all"])
  );

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="rounded-xl border border-base-700 bg-base-900 p-5">
      <h3 className="mb-1 text-sm font-medium text-base-100">เลือกกราฟที่ต้องการ</h3>
      <p className="mb-4 text-sm text-base-400">
        เลือกได้หลายหมวด ระบบจะสร้างกราฟจากข้อมูลที่รวมแล้ว
      </p>

      <div className="flex flex-col gap-2">
        {CHART_CATEGORIES.map((cat) => {
          const isReady = readyCategories.includes(cat.id);
          return (
            <label
              key={cat.id}
              className={[
                "flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition-colors",
                selected.has(cat.id)
                  ? "border-signal-500 bg-signal-500/10"
                  : "border-base-600 bg-base-800 hover:border-base-500",
              ].join(" ")}
            >
              <input
                type="checkbox"
                checked={selected.has(cat.id)}
                onChange={() => toggle(cat.id)}
                className="mt-0.5 h-4 w-4 accent-signal-500"
              />
              <span className="flex-1">
                <span className="block text-sm text-base-100">
                  {cat.label}
                  {isReady && (
                    <span className="ml-2 rounded bg-teal-500/15 px-1.5 py-0.5 text-[11px] font-medium text-teal-400">
                      สร้างแล้ว
                    </span>
                  )}
                </span>
                <span className="block text-xs text-base-400">{cat.description}</span>
              </span>
            </label>
          );
        })}
      </div>

      <button
        onClick={() => onGenerate(Array.from(selected))}
        disabled={selected.size === 0 || generating}
        className="mt-4 w-full rounded-lg bg-signal-500 px-4 py-2.5 text-sm font-medium text-base-950 transition-colors hover:bg-signal-400 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {generating ? "กำลังสร้างกราฟ..." : "สร้างกราฟ"}
      </button>
    </div>
  );
}
