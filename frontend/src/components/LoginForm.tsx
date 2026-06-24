"use client";

import { useState } from "react";
import { DateRangePicker } from "./DateRangePicker";

interface LoginFormProps {
  onSubmit: (data: {
    username: string;
    password: string;
    start_date: string;
    end_date: string;
  }) => void;
  submitting?: boolean;
  errorMessage?: string | null;
}

export function LoginForm({ onSubmit, submitting, errorMessage }: LoginFormProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const canSubmit =
    username.trim() !== "" &&
    password.trim() !== "" &&
    startDate !== "" &&
    endDate !== "" &&
    !submitting;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!canSubmit) return;
        onSubmit({ username, password, start_date: startDate, end_date: endDate });
      }}
      className="rounded-xl border border-base-700 bg-base-900 p-5"
    >
      <div className="mb-4">
        <label className="mb-1.5 block text-sm text-base-300">
          Username (AMR)
        </label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={submitting}
          autoComplete="username"
          placeholder="Enter your AMR username"
          className="w-full rounded-lg border border-base-600 bg-base-800 px-3 py-2.5 text-base-100 placeholder:text-base-500 outline-none transition-colors focus:border-signal-500 disabled:opacity-50"
        />
      </div>

      <div className="mb-5">
        <label className="mb-1.5 block text-sm text-base-300">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={submitting}
          autoComplete="current-password"
          placeholder="Enter your AMR password"
          className="w-full rounded-lg border border-base-600 bg-base-800 px-3 py-2.5 text-base-100 placeholder:text-base-500 outline-none transition-colors focus:border-signal-500 disabled:opacity-50"
        />
        <p className="mt-1.5 text-xs text-base-500">
          ระบบไม่บันทึก username/password ไว้ที่ใดทั้งสิ้น ใช้เพื่อเข้าสู่ระบบครั้งนี้เท่านั้น
        </p>
      </div>

      <div className="mb-5">
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onChange={(s, e) => {
            setStartDate(s);
            setEndDate(e);
          }}
          disabled={submitting}
        />
      </div>

      {errorMessage && (
        <div className="mb-4 rounded-lg border border-signal-700 bg-signal-900/40 px-3 py-2.5 text-sm text-signal-200">
          {errorMessage}
        </div>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="w-full rounded-lg bg-signal-500 px-4 py-2.5 text-sm font-medium text-base-950 transition-colors hover:bg-signal-400 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {submitting ? "กำลังเข้าสู่ระบบ..." : "เริ่มดึงข้อมูล"}
      </button>
    </form>
  );
}
