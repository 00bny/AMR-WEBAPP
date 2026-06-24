"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { JobPublicState } from "@/types/job";

const TERMINAL_STATUSES = new Set(["done", "failed", "cancelled"]);
const PAUSE_STATUSES = new Set(["ready_to_merge", "ready_to_chart"]);

function shouldPause(data: JobPublicState): boolean {
  return (
    TERMINAL_STATUSES.has(data.status) ||
    PAUSE_STATUSES.has(data.status) ||
    data.awaiting_meter_choice
  );
}

export function useJobPolling(jobId: string | null) {
  const [job, setJob] = useState<JobPublicState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const pollOnce = useCallback(async (id: string) => {
    try {
      const data = await api.getJob(id);
      setJob(data);
      setError(null);
      if (shouldPause(data)) stopPolling();
    } catch (e) {
      setError(e instanceof Error ? e.message : "เกิดข้อผิดพลาดในการเชื่อมต่อ");
    }
  }, [stopPolling]);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      return;
    }

    pollOnce(jobId);
    intervalRef.current = setInterval(() => pollOnce(jobId), 1500);

    return () => stopPolling();
  }, [jobId, pollOnce, stopPolling]);

  // Exposed so callers can manually resume polling after an action like
  // "merge" or "generate charts" moves the job out of a paused state.
  const resume = useCallback(() => {
    if (!jobId || intervalRef.current) return;
    pollOnce(jobId);
    intervalRef.current = setInterval(() => pollOnce(jobId), 1500);
  }, [jobId, pollOnce]);

  return { job, error, resume };
}
