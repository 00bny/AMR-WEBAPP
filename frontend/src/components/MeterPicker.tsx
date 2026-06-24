"use client";

import { useState } from "react";
import type { MeterOption } from "@/types/job";

interface MeterPickerProps {
  meters: MeterOption[];
  onConfirm: (selected: string[]) => void;
  submitting?: boolean;
}

export function MeterPicker({ meters, onConfirm, submitting }: MeterPickerProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = (value: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  return (
    <div className="rounded-xl border border-base-700 bg-base-900 p-5">
      <h3 className="mb-1 text-sm font-medium text-base-100">
        พบมิเตอร์หลายตัวในบัญชีนี้
      </h3>
      <p className="mb-4 text-sm text-base-400">
        เลือกมิเตอร์ที่ต้องการดึงข้อมูล (เลือกได้มากกว่า 1 ตัว)
      </p>

      <div className="flex flex-col gap-2">
        {meters.map((m) => (
          <label
            key={m.value}
            className={[
              "flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors",
              selected.has(m.value)
                ? "border-signal-500 bg-signal-500/10"
                : "border-base-600 bg-base-800 hover:border-base-500",
            ].join(" ")}
          >
            <input
              type="checkbox"
              checked={selected.has(m.value)}
              onChange={() => toggle(m.value)}
              className="h-4 w-4 accent-signal-500"
            />
            <span className="text-sm text-base-100">{m.text}</span>
          </label>
        ))}
      </div>

      <button
        onClick={() => onConfirm(Array.from(selected))}
        disabled={selected.size === 0 || submitting}
        className="mt-4 w-full rounded-lg bg-signal-500 px-4 py-2.5 text-sm font-medium text-base-950 transition-colors hover:bg-signal-400 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {submitting ? "กำลังเริ่มดาวน์โหลด..." : "ยืนยันและเริ่มดาวน์โหลด"}
      </button>
    </div>
  );
}
