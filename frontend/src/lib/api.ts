import type { JobPublicState } from "@/types/job";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = `เกิดข้อผิดพลาด (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  createJob: (data: {
    username: string;
    password: string;
    start_date: string;
    end_date: string;
  }) =>
    request<{ job_id: string }>("/api/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getJob: (jobId: string) => request<JobPublicState>(`/api/jobs/${jobId}`),

  selectMeters: (jobId: string, meterValues: string[]) =>
    request<{ ok: true }>(`/api/jobs/${jobId}/meters`, {
      method: "POST",
      body: JSON.stringify({ meter_values: meterValues }),
    }),

  merge: (jobId: string) =>
    request<{ ok: true }>(`/api/jobs/${jobId}/merge`, { method: "POST" }),

  makeCharts: (jobId: string, categories: string[]) =>
    request<{ ok: true }>(`/api/jobs/${jobId}/charts`, {
      method: "POST",
      body: JSON.stringify({ categories }),
    }),

  listFiles: (jobId: string) =>
    request<{
      xls_count: number;
      xlsx_count: number;
      has_merged: boolean;
      chart_categories: Record<string, string[]>;
    }>(`/api/jobs/${jobId}/files`),

  chartImageUrl: (jobId: string, filename: string) =>
    `${API_BASE}/api/jobs/${jobId}/charts/${filename}`,

  downloadZip: async (
    jobId: string,
    selection: {
      include_xls: boolean;
      include_xlsx: boolean;
      include_merged: boolean;
      chart_categories: string[];
    }
  ) => {
    const res = await fetch(`${API_BASE}/api/jobs/${jobId}/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(selection),
    });
    if (!res.ok) throw new ApiError("ดาวน์โหลดไม่สำเร็จ", res.status);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `amr_data_${jobId}.zip`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  deleteJob: (jobId: string) =>
    request<{ ok: true }>(`/api/jobs/${jobId}`, { method: "DELETE" }),
};

export { ApiError };
