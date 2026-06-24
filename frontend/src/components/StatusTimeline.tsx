"use client";

import type { JobStatus } from "@/types/job";

const STEPS: { key: JobStatus[]; label: string }[] = [
  { key: ["logging_in"], label: "เข้าสู่ระบบ AMR" },
  { key: ["downloading"], label: "ดาวน์โหลดข้อมูลรายเดือน" },
  { key: ["converting"], label: "แปลงไฟล์ xls → xlsx" },
  { key: ["ready_to_merge", "merging"], label: "รวมไฟล์ทุกเดือน" },
  { key: ["ready_to_chart", "charting"], label: "สร้างกราฟวิเคราะห์" },
  { key: ["done"], label: "เสร็จสมบูรณ์" },
];

function stepState(
  stepKeys: JobStatus[],
  currentStatus: JobStatus,
  stepIndex: number,
  currentIndex: number
): "done" | "active" | "pending" {
  if (currentStatus === "failed" || currentStatus === "cancelled") {
    return stepIndex < currentIndex ? "done" : "pending";
  }
  if (stepIndex < currentIndex) return "done";
  if (stepIndex === currentIndex) return "active";
  return "pending";
}

export function StatusTimeline({ status }: { status: JobStatus }) {
  const currentIndex = STEPS.findIndex((s) => s.key.includes(status));
  const effectiveIndex = currentIndex === -1 ? 0 : currentIndex;

  return (
    <div className="flex flex-col">
      {STEPS.map((step, i) => {
        const state = stepState(step.key, status, i, effectiveIndex);
        const isLast = i === STEPS.length - 1;
        return (
          <div key={step.label} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div
                className={[
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 text-[11px] font-medium transition-colors",
                  state === "done" &&
                    "border-signal-500 bg-signal-500 text-base-950",
                  state === "active" &&
                    "border-signal-500 bg-base-950 text-signal-500",
                  state === "pending" &&
                    "border-base-600 bg-base-900 text-base-500",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {state === "done" ? "✓" : i + 1}
              </div>
              {!isLast && (
                <div
                  className={[
                    "w-px flex-1 min-h-[28px]",
                    state === "done" ? "bg-signal-500" : "bg-base-600",
                  ].join(" ")}
                />
              )}
            </div>
            <div className="pb-7">
              <p
                className={[
                  "text-sm font-medium leading-6",
                  state === "pending" ? "text-base-400" : "text-base-100",
                ].join(" ")}
              >
                {step.label}
              </p>
              {state === "active" && (
                <span className="mt-0.5 inline-flex items-center gap-1.5 text-xs text-signal-400">
                  <span className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-signal-400" />
                  กำลังทำงาน
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
