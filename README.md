# AMR Load Profile — เว็บดึงและวิเคราะห์ข้อมูล Load Profile

เว็บแอปสำหรับดึงข้อมูล Load Profile จากระบบ AMR (PEA), แปลงไฟล์, รวมข้อมูลทุกเดือน,
และสร้างกราฟวิเคราะห์ — ทั้งหมดผ่านหน้าเว็บเดียว ไม่ต้องลงโปรแกรมเพิ่ม

## โครงสร้างโปรเจกต์

```
amr-webapp/
├── backend/      FastAPI + Selenium  (deploy บน Render, free tier)
└── frontend/     Next.js + Tailwind  (deploy บน Vercel, free tier)
```

ทั้งสองส่วนแยก deploy กันคนละที่ เพราะ backend ต้องรัน Selenium (เปิด Chrome จริง)
ซึ่ง Vercel (serverless) ทำไม่ได้ ส่วน frontend เป็นหน้าเว็บธรรมดาที่ deploy บน
Vercel ได้สบายๆ

ค่าใช้จ่ายรวม: **$0/เดือน** (ทั้ง Render free และ Vercel free ไม่ต้องผูกบัตรเครดิต)

---

## ภาพรวมการทำงาน

1. ผู้ใช้กรอก username/password ของ AMR + เลือกวันเริ่มต้น-วันสิ้นสุดที่ต้องการ (เลือกวัน/เดือน/ปีได้ละเอียด ไม่ต้องเป็นทั้งเดือน)
2. Backend เปิด headless Chrome, login, ตรวจดูว่ามีกี่มิเตอร์ในบัญชีนี้
3. ถ้ามีมิเตอร์เดียว → ดึงข้อมูลอัตโนมัติ / ถ้ามีหลายมิเตอร์ → ให้ผู้ใช้เลือกก่อน
4. ดาวน์โหลดไฟล์ .xls ทีละเดือน แปลงเป็น .xlsx ทันทีที่ดาวน์โหลดเสร็จ (พร้อม progress %)
5. ผู้ใช้กด "รวมไฟล์" → รวมทุกเดือนเป็นไฟล์เดียว พร้อม clean ข้อมูล (3 รูปแบบไฟล์ที่รองรับ)
6. ผู้ใช้เลือกหมวดกราฟที่ต้องการ → ระบบสร้างกราฟ (matplotlib) ให้ดูในเว็บ
7. ผู้ใช้เลือกว่าจะดาวน์โหลดไฟล์ไหนบ้าง (.xls / .xlsx / ไฟล์รวม / กราฟ) → ได้ไฟล์ .zip เดียว
8. ไฟล์ทั้งหมดถูกลบจาก server อัตโนมัติหลังจาก 30 นาที (หรือสูงสุด 2 ชม.) — ไม่มีการเก็บข้อมูลถาวร

**Username/password ไม่ถูกบันทึกที่ไหนเลย** ส่งผ่าน HTTPS ใช้ตอน login เท่านั้น
แล้วลบออกจาก memory ทันทีที่ดาวน์โหลดเสร็จหรือ login ไม่สำเร็จ

---

## รันทดสอบในเครื่อง (Local Development)

### Backend

ต้องมี Docker (เพราะต้องมี Chromium + chromedriver) — ใช้ Docker เป็นวิธีที่ง่ายสุด:

```bash
cd backend
docker build -t amr-backend .
docker run -p 8000:8000 -e ALLOWED_ORIGINS=http://localhost:3000 amr-backend
```

ทดสอบว่ารันอยู่: เปิด http://localhost:8000/health ควรเห็น `{"ok": true}`

หรือถ้าไม่อยากใช้ Docker (ต้องลง Chromium/chromedriver เองในเครื่อง):
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # แก้ CHROME_BINARY / CHROMEDRIVER_BINARY ให้ตรงกับเครื่องคุณ
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # ค่า default ชี้ไป localhost:8000 อยู่แล้ว ถ้ารัน backend local
npm run dev
```

เปิด http://localhost:3000

---

## Deploy ขึ้นใช้งานจริง (Production)

### ขั้นที่ 1 — Push โค้ดขึ้น GitHub

สร้าง repo ใหม่บน GitHub แล้ว push โฟลเดอร์นี้ทั้งหมดขึ้นไป (ทั้ง `backend/` และ
`frontend/` อยู่ใน repo เดียวกันได้ — เดี๋ยว Render และ Vercel จะตั้งให้ดูแค่
โฟลเดอร์ที่เกี่ยวข้องของแต่ละฝั่ง)

### ขั้นที่ 2 — Deploy Backend บน Render

1. ไปที่ [render.com](https://render.com) สมัครฟรี (ไม่ต้องผูกบัตร)
2. New → Web Service → เชื่อมต่อ GitHub repo ที่ push ไว้
3. ตั้งค่า:
   - **Root Directory**: `backend`
   - **Runtime**: Docker (Render จะเจอ `Dockerfile` อัตโนมัติ)
   - **Plan**: Free
4. ใส่ Environment Variables (ตาม `.env.example`):
   - `ALLOWED_ORIGINS` = (ใส่ทีหลังหลังจากได้ URL ของ Vercel แล้ว เช่น `https://your-app.vercel.app`)
   - `MAX_CONCURRENT_SCRAPES` = `1`
   - `TEMP_ROOT` = `/tmp/amr_jobs`
   - `JOB_TTL_AFTER_DONE_SECONDS` = `1800`
   - `JOB_TTL_MAX_SECONDS` = `7200`
5. Deploy แล้วรอ build เสร็จ (ครั้งแรกใช้เวลาสักหน่อยเพราะต้องลง Chromium)
6. จะได้ URL ประมาณ `https://amr-load-profile-backend.onrender.com` — เก็บไว้ใช้ขั้นต่อไป
7. ทดสอบ: เปิด `https://YOUR-RENDER-URL.onrender.com/health` ควรเห็น `{"ok":true}`

> ⚠️ **Free tier จะ sleep หลังไม่มีคนใช้ 15 นาที** ผู้ใช้คนแรกของวันจะต้องรอ
> ~30-50 วินาทีให้ server ตื่นก่อนเริ่มงานได้ ถัดจากนั้นจะเร็วเป็นปกติ
> ตามที่ตัดสินใจไว้ว่ารับได้

### ขั้นที่ 3 — Deploy Frontend บน Vercel

1. ไปที่ [vercel.com](https://vercel.com) สมัครฟรี
2. New Project → เชื่อมต่อ GitHub repo เดียวกัน
3. ตั้งค่า:
   - **Root Directory**: `frontend`
   - Framework Preset: Next.js (เจอเองอัตโนมัติ)
4. ใส่ Environment Variable:
   - `NEXT_PUBLIC_API_BASE_URL` = URL ของ Render จากขั้นที่ 2 (เช่น `https://amr-load-profile-backend.onrender.com`)
5. Deploy

### ขั้นที่ 4 — เชื่อมสองฝั่งกลับ

กลับไปที่ Render → Environment → แก้ `ALLOWED_ORIGINS` ให้เป็น URL จริงของ Vercel
ที่ได้ในขั้นที่ 3 (เช่น `https://your-app.vercel.app`) → Save (Render จะ redeploy
ให้อัตโนมัติ)

เสร็จแล้ว — เปิด URL ของ Vercel ได้เลย ผู้ใช้ทั่วไปเข้าใช้ได้ทันทีไม่ต้องลงโปรแกรมอะไร

---

## ข้อจำกัดที่ควรรู้

- **เลือกโฟลเดอร์ปลายทางไม่ได้**: เบราว์เซอร์ไม่อนุญาตให้เว็บไซต์เลือกโฟลเดอร์ในเครื่อง
  ผู้ใช้โดยตรง ระบบจึงรวมไฟล์เป็น `.zip` แล้วให้กด "ดาวน์โหลด" ตามปกติ (ไปที่โฟลเดอร์
  Downloads ตาม default ของเบราว์เซอร์)
- **Cold start ของ Render free tier**: รอ ~30-50 วิ ถ้าไม่มีคนใช้นานเกิน 15 นาที
- **รันพร้อมกันได้จำกัด**: ตั้งไว้ที่ 1 job ต่อครั้ง (ปรับได้ผ่าน `MAX_CONCURRENT_SCRAPES`
  แต่ต้องดู RAM ของแผนที่ใช้ — free tier มี 512MB ซึ่งพอสำหรับ 1 Chrome instance)
- **ความเสี่ยงจากตัวเว็บ AMR เปลี่ยนโครงสร้างหน้าเว็บ**: scraper พึ่งพา element ID
  เฉพาะของหน้า AMR (เช่น `txtUsername`, `ddlMeter`, `btnSubmit`) ถ้าทาง PEA
  เปลี่ยนหน้าเว็บ จะต้องอัปเดต `backend/app/scraper/amr_scraper.py` ตาม
- **ไฟล์ชั่วคราวเท่านั้น**: ไม่มีฐานข้อมูลเก็บถาวร ทุกอย่างอยู่ใน RAM/disk ชั่วคราว
  ของ job นั้นๆ และถูกลบทิ้งหลัง 30 นาที-2 ชม. ตามที่ตั้งไว้

## Troubleshooting

**ขึ้น "เกิดข้อผิดพลาด (404)" ทันทีที่กด "เริ่มดึงข้อมูล" ตอนรันในเครื่อง**

สาเหตุที่พบบ่อยที่สุด: ไฟล์ `frontend/.env.local` ยังชี้ไป URL ของ production
(เช่น `https://your-backend.onrender.com`) อยู่ ทั้งที่ backend จริงรันอยู่ที่
`localhost:8000` ในเครื่อง — ตรวจสอบว่า:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

แล้ว **restart `npm run dev`** ใหม่ (จำเป็นต้อง restart เพราะ Next.js อ่านค่า
`NEXT_PUBLIC_*` ตอน start server เท่านั้น แก้ไฟล์แล้วเปลี่ยนค่าทันทีโดยไม่ restart
จะไม่มีผล)

**Backend ขึ้น "Cannot connect to the Docker daemon"**

แปลว่า Docker Desktop ยังไม่ได้เปิด — เปิดแอป Docker Desktop ก่อน แล้วรอจน
มันพร้อม (ไอคอนใน menu bar จะหยุดกระพริบ) ก่อนรัน `docker build` อีกครั้ง



## โครงสร้างไฟล์โดยละเอียด

```
backend/
├── app/
│   ├── main.py                 FastAPI entry point + CORS + cleanup loop
│   ├── core/config.py          การตั้งค่าทั้งหมดจาก environment variables
│   ├── jobs/
│   │   ├── models.py           โครงสร้างข้อมูล JobState
│   │   ├── store.py            in-memory job store + semaphore queue
│   │   └── runner.py           orchestration: login→scrape→convert→merge→chart
│   ├── scraper/amr_scraper.py  Selenium logic (ย้ายมาจาก AMR_REE.py)
│   ├── processing/
│   │   ├── convert.py          xls→xlsx (ย้ายมาจาก convert_xls.py)
│   │   ├── merge.py            รวม+clean ไฟล์ (ย้ายมาจาก merge.py)
│   │   └── charts.py           สร้างกราฟ 7 หมวด (ย้ายมาจาก Load_Profile_Analysis.ipynb)
│   └── routers/jobs.py         API endpoints ทั้งหมด
├── Dockerfile                  Python + Chromium + chromedriver
├── render.yaml                 ค่าเริ่มต้นสำหรับ deploy บน Render
└── requirements.txt

frontend/
├── src/
│   ├── app/page.tsx             หน้าหลัก ผูกทุก component ตาม job status
│   ├── components/              LoginForm, StatusTimeline, ProgressCard,
│   │                            MeterPicker, ChartSelector, ChartGallery,
│   │                            DownloadPanel, MonthRangePicker
│   ├── lib/api.ts                API client เรียก backend
│   ├── lib/useJobPolling.ts      poll สถานะ job ทุก 1.5 วิ
│   └── types/job.ts              TypeScript types + รายชื่อหมวดกราฟ
└── package.json
```
