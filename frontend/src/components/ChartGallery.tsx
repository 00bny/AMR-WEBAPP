"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { CHART_CATEGORIES } from "@/types/job";

interface ChartGalleryProps {
  jobId: string;
  readyCategories: string[];
}

export function ChartGallery({ jobId, readyCategories }: ChartGalleryProps) {
  const [filesByCategory, setFilesByCategory] = useState<Record<string, string[]>>({});

  // readyCategories is a new array on every poll tick even when its contents
  // are unchanged, which would re-trigger the effect every 1.5s forever if
  // we depended on the array itself. Depend on a stable string key instead,
  // so the fetch only re-runs when the actual set of ready categories changes.
  const readyKey = useMemo(() => [...readyCategories].sort().join(","), [readyCategories]);

  useEffect(() => {
    if (readyCategories.length === 0) return;
    api.listFiles(jobId).then((res) => setFilesByCategory(res.chart_categories));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, readyKey]);

  if (readyCategories.length === 0) return null;

  return (
    <div className="rounded-xl border border-base-700 bg-base-900 p-5">
      <h3 className="mb-4 text-sm font-medium text-base-100">ตัวอย่างกราฟ</h3>
      <div className="flex flex-col gap-6">
        {readyCategories.map((catId) => {
          const cat = CHART_CATEGORIES.find((c) => c.id === catId);
          const files = filesByCategory[catId] || [];
          if (files.length === 0) return null;
          return (
            <div key={catId}>
              <p className="mb-2 text-sm font-medium text-base-200">
                {cat?.label || catId}
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {files.map((filename) => (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={filename}
                    src={api.chartImageUrl(jobId, filename)}
                    alt={filename}
                    className="aspect-video w-full rounded-md border border-base-700 object-cover bg-base-800"
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
