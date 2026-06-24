"use client";

interface CalendarProps {
  year: number;
  month: number; // 1-12
  selectedDay: number | null;
  onSelectDay: (day: number) => void;
  onNavigate: (year: number, month: number) => void;
}

const WEEKDAY_LABELS = ["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"];
const MONTH_LABELS = [
  "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
  "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
];

function daysInMonth(year: number, month: number): number {
  // month is 1-indexed; passing it as the JS (0-indexed) month with day 0
  // lands on the last day of the previous JS month, i.e. our target month.
  return new Date(year, month, 0).getDate();
}

function firstWeekday(year: number, month: number): number {
  return new Date(year, month - 1, 1).getDay(); // 0 = Sunday
}

export function Calendar({
  year,
  month,
  selectedDay,
  onSelectDay,
  onNavigate,
}: CalendarProps) {
  const today = new Date();
  const isCurrentMonth =
    today.getFullYear() === year && today.getMonth() + 1 === month;
  const todayDay = isCurrentMonth ? today.getDate() : null;

  const totalDays = daysInMonth(year, month);
  const leadingBlanks = firstWeekday(year, month);
  const cells: (number | null)[] = [
    ...Array.from({ length: leadingBlanks }, () => null),
    ...Array.from({ length: totalDays }, (_, i) => i + 1),
  ];

  const goPrev = () => {
    if (month === 1) onNavigate(year - 1, 12);
    else onNavigate(year, month - 1);
  };
  const goNext = () => {
    if (month === 12) onNavigate(year + 1, 1);
    else onNavigate(year, month + 1);
  };

  return (
    <div className="w-72 rounded-xl border border-base-600 bg-base-800 p-3 shadow-2xl">
      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={goPrev}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-base-300 transition-colors hover:bg-base-700 hover:text-base-100"
          aria-label="เดือนก่อนหน้า"
        >
          ‹
        </button>
        <p className="text-sm font-medium text-base-100">
          {MONTH_LABELS[month - 1]} {year}
        </p>
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={goNext}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-base-300 transition-colors hover:bg-base-700 hover:text-base-100"
          aria-label="เดือนถัดไป"
        >
          ›
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center">
        {WEEKDAY_LABELS.map((d) => (
          <div key={d} className="py-1 text-xs font-medium text-base-400">
            {d}
          </div>
        ))}
        {cells.map((day, i) =>
          day === null ? (
            <div key={`blank-${i}`} />
          ) : (
            <button
              key={day}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => onSelectDay(day)}
              className={[
                "flex h-8 w-8 items-center justify-center rounded-lg text-sm transition-colors",
                day === selectedDay
                  ? "bg-signal-500 font-semibold text-base-950"
                  : day === todayDay
                    ? "border border-signal-500 text-signal-400"
                    : "text-base-100 hover:bg-base-700",
              ].join(" ")}
            >
              {day}
            </button>
          )
        )}
      </div>
    </div>
  );
}
