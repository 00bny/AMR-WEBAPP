export type JobStatus =
  | "queued"
  | "logging_in"
  | "downloading"
  | "converting"
  | "ready_to_merge"
  | "merging"
  | "ready_to_chart"
  | "charting"
  | "done"
  | "failed"
  | "cancelled";

export interface MeterOption {
  value: string;
  text: string;
}

export interface MonthResult {
  label: string;
  success: boolean;
  error: string | null;
}

export interface JobPublicState {
  job_id: string;
  status: JobStatus;
  progress_pct: number;
  current_step: string;
  total_months: number;
  completed_months: number;
  available_meters: MeterOption[];
  awaiting_meter_choice: boolean;
  months: MonthResult[];
  has_merged_file: boolean;
  chart_categories_ready: string[];
  error_message: string | null;
}

export interface ChartCategory {
  id: string;
  label: string;
  description: string;
}

export const CHART_CATEGORIES: ChartCategory[] = [
  {
    id: "dotplot_all",
    label: "ภาพรวมทั้งหมด (Dot plot)",
    description: "กระจายค่าการใช้พลังงานทุกจุดข้อมูล แยกตามช่วงเวลาของวัน",
  },
  {
    id: "boxplot_violin_all",
    label: "ภาพรวมทั้งหมด (Box + Violin)",
    description: "ดูการกระจายตัวและความหนาแน่นของข้อมูลในแต่ละช่วงเวลา",
  },
  {
    id: "by_day_of_week",
    label: "แยกตามวันในสัปดาห์",
    description: "เปรียบเทียบรูปแบบการใช้พลังงานของแต่ละวัน จันทร์ถึงอาทิตย์",
  },
  {
    id: "by_month",
    label: "เปรียบเทียบรายเดือน",
    description: "ดูแนวโน้มการใช้พลังงานในแต่ละเดือนเทียบกัน",
  },
  {
    id: "by_month_detail",
    label: "รายเดือนแบบละเอียด",
    description: "แยกแต่ละเดือนตามช่วงเวลาของวัน ดูรายละเอียดเชิงลึก",
  },
  {
    id: "weekdays_only",
    label: "เฉพาะวันธรรมดา (รายเดือน)",
    description: "ตัดเสาร์-อาทิตย์ออก ดูเฉพาะรูปแบบวันทำงาน",
  },
  {
    id: "weekend_only",
    label: "เฉพาะเสาร์-อาทิตย์",
    description: "ดูรูปแบบการใช้พลังงานเฉพาะวันหยุดสุดสัปดาห์",
  },
];
