"use client";

import { useEffect, useRef, useState } from "react";
import { Calendar } from "./Calendar";

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function lastDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

function parseInitial(value: string) {
  if (!value) return { month: "", year: "", day: null as number | null };
  const [y, m, d] = value.split("-");
  return { month: m || "", year: y || "", day: d ? Number(d) : null };
}

interface DateFieldProps {
  label: string;
  value: string; // "YYYY-MM-DD" or ""
  onChange: (value: string) => void;
  /** Default day to use when the user only types month/year without
   * picking an exact day on the calendar: 1st of the month for "start",
   * last day of the month for "end". */
  mode: "start" | "end";
  disabled?: boolean;
}

export function DateField({ label, value, onChange, mode, disabled }: DateFieldProps) {
  // Seed local state once, on mount, from the initial value - this field
  // owns its own state from then on and is the single source of truth.
  // (The old Combobox-based picker re-derived its display from the parent's
  // value every render, which kept wiping out the user's selection before
  // all three parts were filled in. This component never does that.)
  const initial = useRef(parseInitial(value)).current;
  const [monthText, setMonthText] = useState(initial.month);
  const [yearText, setYearText] = useState(initial.year);
  const [dayPicked, setDayPicked] = useState<number | null>(initial.day);
  const [isOpen, setIsOpen] = useState(false);
  const [viewYear, setViewYear] = useState(
    initial.year ? Number(initial.year) : new Date().getFullYear()
  );
  const [viewMonth, setViewMonth] = useState(
    initial.month ? Number(initial.month) : new Date().getMonth() + 1
  );
  const containerRef = useRef<HTMLDivElement>(null);

  // Compose and emit the full date upward whenever the underlying parts
  // change. Intentionally excludes `onChange`/`mode` identity from causing
  // re-runs beyond what's needed - see comment below.
  useEffect(() => {
    const m = parseInt(monthText, 10);
    const y = parseInt(yearText, 10);
    const monthValid = m >= 1 && m <= 12;
    const yearValid = yearText.length === 4 && y > 0;
    if (!monthValid || !yearValid) {
      onChange("");
      return;
    }
    const maxDay = lastDayOfMonth(y, m);
    const fallbackDay = mode === "start" ? 1 : maxDay;
    const effectiveDay = dayPicked ? Math.min(dayPicked, maxDay) : fallbackDay;
    onChange(`${y}-${pad2(m)}-${pad2(effectiveDay)}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [monthText, yearText, dayPicked]);

  useEffect(() => {
    function handleOutsideOrEscape(e: MouseEvent | KeyboardEvent) {
      if (e instanceof KeyboardEvent) {
        if (e.key === "Escape") setIsOpen(false);
        return;
      }
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleOutsideOrEscape);
    document.addEventListener("keydown", handleOutsideOrEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutsideOrEscape);
      document.removeEventListener("keydown", handleOutsideOrEscape);
    };
  }, []);

  const openCalendar = () => {
    const m = parseInt(monthText, 10);
    const y = parseInt(yearText, 10);
    setViewMonth(m >= 1 && m <= 12 ? m : new Date().getMonth() + 1);
    setViewYear(yearText.length === 4 && y > 0 ? y : new Date().getFullYear());
    setIsOpen((o) => !o);
  };

  const handleSelectDay = (day: number) => {
    setDayPicked(day);
    setMonthText(pad2(viewMonth));
    setYearText(String(viewYear));
    setIsOpen(false);
  };

  return (
    <div ref={containerRef} className="relative">
      <label className="mb-1.5 block text-sm text-base-300">{label}</label>
      <div className="flex items-center gap-2">
        <input
          type="text"
          inputMode="numeric"
          maxLength={2}
          placeholder="MM"
          value={monthText}
          disabled={disabled}
          onChange={(e) => setMonthText(e.target.value.replace(/\D/g, "").slice(0, 2))}
          className="w-16 rounded-lg border border-base-600 bg-base-800 px-2 py-2.5 text-center text-base-100 outline-none transition-colors focus:border-signal-500 disabled:opacity-50"
        />
        <span className="text-base-500">/</span>
        <input
          type="text"
          inputMode="numeric"
          maxLength={4}
          placeholder="YYYY"
          value={yearText}
          disabled={disabled}
          onChange={(e) => setYearText(e.target.value.replace(/\D/g, "").slice(0, 4))}
          className="w-20 rounded-lg border border-base-600 bg-base-800 px-2 py-2.5 text-center text-base-100 outline-none transition-colors focus:border-signal-500 disabled:opacity-50"
        />
        <button
          type="button"
          disabled={disabled}
          onClick={openCalendar}
          className="flex h-[42px] w-[42px] shrink-0 items-center justify-center rounded-lg border border-base-600 bg-base-800 text-base-300 transition-colors hover:border-signal-500 hover:text-signal-400 disabled:opacity-50"
          aria-label="เปิดปฏิทิน"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="5" width="18" height="16" rx="2" />
            <path d="M3 9h18M8 3v4M16 3v4" />
          </svg>
        </button>
      </div>

      {dayPicked && monthText && yearText && (
        <p className="mt-1.5 text-xs text-base-500">
          เลือกวันที่: {pad2(dayPicked)}/{monthText}/{yearText}
        </p>
      )}

      {isOpen && (
        <div className="absolute z-30 mt-2">
          <Calendar
            year={viewYear}
            month={viewMonth}
            selectedDay={dayPicked}
            onSelectDay={handleSelectDay}
            onNavigate={(y, m) => {
              setViewYear(y);
              setViewMonth(m);
            }}
          />
        </div>
      )}
    </div>
  );
}
