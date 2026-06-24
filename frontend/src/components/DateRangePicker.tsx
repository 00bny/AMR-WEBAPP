"use client";

import { DateField } from "./DateField";

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (start: string, end: string) => void;
  disabled?: boolean;
}

export function DateRangePicker({
  startDate,
  endDate,
  onChange,
  disabled,
}: DateRangePickerProps) {
  return (
    <div className="flex flex-col gap-4">
      <DateField
        label="วันเริ่มต้น"
        value={startDate}
        onChange={(v) => onChange(v, endDate)}
        mode="start"
        disabled={disabled}
      />
      <DateField
        label="วันสิ้นสุด"
        value={endDate}
        onChange={(v) => onChange(startDate, v)}
        mode="end"
        disabled={disabled}
      />
    </div>
  );
}
