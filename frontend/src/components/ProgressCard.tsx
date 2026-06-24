"use client";

import type { JobPublicState } from "@/types/job";

export function ProgressCard({ job }: { job: JobPublicState }) {
  const pct = Math.round(job.progress_pct);
  const isDownloading = job.status === "downloading" || job.status === "converting";

  return (
    <div className="rounded-xl border border-base-700 bg-base-900 p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <p className="text-sm text-base-300">{job.current_step}</p>
        <p className="text-mono-tnum text-2xl font-semibold text-signal-400">
          {pct}%
        </p>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-base-700">
        <div
          className="h-full rounded-full bg-gradient-to-r from-signal-600 to-signal-400 transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>

      {isDownloading && job.total_months > 0 && (
        <p className="mt-3 text-mono-tnum text-xs text-base-400">
          {job.completed_months} / {job.total_months} เดือน
        </p>
      )}

      {job.months.length > 0 && (
        <div className="mt-4 grid grid-cols-3 gap-1.5 sm:grid-cols-4">
          {job.months.map((m) => (
            <div
              key={m.label}
              title={m.error || undefined}
              className={[
                "rounded-md px-2 py-1.5 text-center text-xs font-medium",
                m.success
                  ? "bg-teal-500/15 text-teal-400"
                  : "bg-base-600/40 text-base-300",
              ].join(" ")}
            >
              {m.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
