import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AMR Load Profile",
  description: "ดึงและวิเคราะห์ข้อมูล Load Profile จากระบบ AMR",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th">
      <body className="bg-base-950 text-base-100 antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
