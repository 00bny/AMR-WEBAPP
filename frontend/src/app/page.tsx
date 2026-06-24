"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useJobPolling } from "@/lib/useJobPolling";
import { LoginForm } from "@/components/LoginForm";
import { StatusTimeline } from "@/components/StatusTimeline";
import { ProgressCard } from "@/components/ProgressCard";
import { MeterPicker } from "@/components/MeterPicker";
import { ChartSelector } from "@/components/ChartSelector";
import { ChartGallery } from "@/components/ChartGallery";
import { DownloadPanel } from "@/components/DownloadPanel";

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);

  const { job, error: pollError, resume } = useJobPolling(jobId);

  const handleStart = async (data: {
    username: string;
    password: string;
    start_date: string;
    end_date: string;
  }) => {
    setSubmitting(true);
    setFormError(null);
    try {
      const res = await api.createJob(data);
      setJobId(res.job_id);
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองใหม่");
    } finally {
      setSubmitting(false);
    }
  };

  const handleMeterConfirm = async (meterValues: string[]) => {
    if (!jobId) return;
    setActionPending(true);
    try {
      await api.selectMeters(jobId, meterValues);
      resume();
    } finally {
      setActionPending(false);
    }
  };

  const handleMerge = async () => {
    if (!jobId) return;
    setActionPending(true);
    try {
      await api.merge(jobId);
      resume();
    } finally {
      setActionPending(false);
    }
  };

  const handleGenerateCharts = async (categories: string[]) => {
    if (!jobId) return;
    setActionPending(true);
    try {
      await api.makeCharts(jobId, categories);
      resume();
    } finally {
      setActionPending(false);
    }
  };

  const handleDownload = async (selection: {
    include_xls: boolean;
    include_xlsx: boolean;
    include_merged: boolean;
    chart_categories: string[];
  }) => {
    if (!jobId) return;
    setActionPending(true);
    try {
      await api.downloadZip(jobId, selection);
    } catch {
      setFormError("ดาวน์โหลดไฟล์ไม่สำเร็จ กรุณาลองใหม่");
    } finally {
      setActionPending(false);
    }
  };

  const handleReset = async () => {
    if (jobId) {
      try {
        await api.deleteJob(jobId);
      } catch {
        /* best effort */
      }
    }
    setJobId(null);
    setFormError(null);
  };

  return (
    <main className="bg-grid min-h-screen">
      <div className="mx-auto max-w-2xl px-4 py-10 sm:py-16">
        <header className="mb-8">
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-signal-500">
            AMR Load Profile
          </p>
          <h1 className="text-2xl font-semibold text-base-100 sm:text-3xl">
            ดึงและวิเคราะห์ข้อมูลการใช้พลังงาน
          </h1>
          <p className="mt-2 text-sm text-base-400">
            กรอกข้อมูลบัญชี AMR และช่วงเดือนที่ต้องการ ระบบจะดาวน์โหลด แปลงไฟล์ รวมข้อมูล
            และสร้างกราฟให้อัตโนมัติ
          </p>
        </header>

        {!jobId && (
          <LoginForm onSubmit={handleStart} submitting={submitting} errorMessage={formError} />
        )}

        {jobId && job && (
          <div className="flex flex-col gap-5">
            <div className="rounded-xl border border-base-700 bg-base-900 p-5">
              <StatusTimeline status={job.status} />
            </div>

            {(job.status === "logging_in" ||
              job.status === "downloading" ||
              job.status === "converting" ||
              job.status === "merging" ||
              job.status === "charting") && <ProgressCard job={job} />}

            {job.awaiting_meter_choice && (
              <MeterPicker
                meters={job.available_meters}
                onConfirm={handleMeterConfirm}
                submitting={actionPending}
              />
            )}

            {job.status === "ready_to_merge" && (
              <div className="rounded-xl border border-base-700 bg-base-900 p-5">
                <p className="mb-3 text-sm text-base-300">{job.current_step}</p>
                <button
                  onClick={handleMerge}
                  disabled={actionPending}
                  className="w-full rounded-lg bg-signal-500 px-4 py-2.5 text-sm font-medium text-base-950 transition-colors hover:bg-signal-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {actionPending ? "กำลังรวมไฟล์..." : "รวมไฟล์ทุกเดือน"}
                </button>
              </div>
            )}

            {(job.status === "ready_to_chart" || job.status === "done") && (
              <ChartSelector
                onGenerate={handleGenerateCharts}
                generating={actionPending}
                readyCategories={job.chart_categories_ready}
              />
            )}

            {job.chart_categories_ready.length > 0 && (
              <ChartGallery jobId={jobId} readyCategories={job.chart_categories_ready} />
            )}

            {job.has_merged_file && (
              <DownloadPanel
                hasMerged={job.has_merged_file}
                readyChartCategories={job.chart_categories_ready}
                onDownload={handleDownload}
                downloading={actionPending}
              />
            )}

            {job.status === "failed" && (
              <div className="rounded-xl border border-signal-700 bg-signal-900/30 p-5">
                <p className="text-sm text-signal-200">
                  {job.error_message || "เกิดข้อผิดพลาดที่ไม่คาดคิด"}
                </p>
              </div>
            )}

            {pollError && (
              <div className="rounded-xl border border-base-600 bg-base-800 p-4 text-sm text-base-300">
                {pollError}
              </div>
            )}

            <button
              onClick={handleReset}
              className="self-start text-sm text-base-400 underline-offset-4 hover:text-base-200 hover:underline"
            >
              เริ่มงานใหม่
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
