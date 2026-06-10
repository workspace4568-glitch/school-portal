# Proper Child Academy — School Portal

A full-featured, production-ready school management portal built with Flask + SQLAlchemy.

---

## Features

### Public (No login required)
- View school announcements
- Download forms, timetables and documents
- View staff directory
- Check results using Student Code

### Admin (`/admin` — password protected)
- **Dashboard** — live stats and quick info
- **Students** — add/edit/delete, auto-generated student codes
- **Classes & Subjects** — create classes, assign form teachers, configure subjects with CA/Exam weighting
- **Teachers** — manage staff, control public visibility
- **Attendance** — mark daily attendance by class (Present / Absent / Late)
- **Results** — enter CA + Exam scores per subject, auto-grade (A1–F9), auto-calculate positions
- **Fee Payments** — define fee types, record payments, auto-generate receipt numbers
- **Announcements** — post/publish/pin notices
- **Downloads** — upload and manage files (PDF, DOCX, etc.)
- **Reports** — printable class lists and grade sheets
- **Appearance** — 10 preset looks, 20 colour schemes, custom colour pickers, sidebar styles, border radius
- **Settings** — school name, logo, motto, address, contact, academic year/term

### Result Checker
Students/parents visit the site, click **Results**, enter their **Student Code** (e.g. `PCA20240001`) and view/print their term result slip with class position.

---

## Deploy to Render

### Option A — Blueprint (easiest)
1. Push this folder to a GitHub repo
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your repo — Render reads `render.yaml` automatically
4. Click **Apply**

### Option B — Manual Web Service
1. **New** → **Web Service** → connect repo
2. Set:
   - Runtime: **Python 3**
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app --workers 1 --threads 4 --bind 0.0.0.0:$PORT`
3. Add **Disk**: Mount Path `/data`, Size 1 GB
4. Add **Environment Variables**:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | any long random string |
| `ADMIN_PASSWORD` | your chosen password |
| `DATABASE_URL` | `sqlite:////data/nexarion.db` |
| `RENDER` | `true` |

---

## Local Development

```bash
pip install -r requirements.txt
python app.py
# Visit http://localhost:5000
# Admin: http://localhost:5000/admin
```

---

## Default Admin Password

```
admin2024
```

Change via `ADMIN_PASSWORD` environment variable on Render.

---

## Student Code Format

Codes are auto-generated on student creation:

```
PCA20240001
^^^        = School short name (set in Settings)
   ^^^^    = Year of enrollment
       ^^^^ = Sequential number
```

Example: `PCA20240001`, `PCA20240002`, `PCA20250001`

---

## Grading System (WAEC Style)

| Grade | Range | Remark |
|-------|-------|--------|
| A1 | 75–100 | Excellent |
| B2 | 70–74 | Very Good |
| B3 | 65–69 | Good |
| C4 | 60–64 | Credit |
| C5 | 55–59 | Credit |
| C6 | 50–54 | Credit |
| D7 | 45–49 | Pass |
| E8 | 40–44 | Pass |
| F9 | 0–39 | Fail |

---

## File Structure

```
school-portal/
├── app.py              ← Flask backend (49 routes, 12 models)
├── requirements.txt
├── Procfile
├── render.yaml
├── README.md
└── templates/
    └── index.html      ← Full SPA frontend (Font Awesome icons)
```

---

## URLs

| URL | Description |
|-----|-------------|
| `/` | Public home — announcements |
| `/results` | Result checker |
| `/admin` | Admin login & panel |
| `/health` | Health check (used by Render) |
| `/api/...` | REST API endpoints |

---

## Customization Quick Guide

After deploying:

1. Go to `/admin` → log in
2. **Settings** → set school name, logo, motto, address, phone, email
3. **Appearance** → choose a preset or pick custom colours
4. **Classes** → create your classes (e.g. JSS1A, JSS2B, SS1A)
5. **Teachers** → add teaching staff
6. **Classes** → assign form teachers, add subjects per class
7. **Students** → enrol students — codes are auto-generated
8. **Announcements** → post your first notice
9. Share student codes with parents for result checking
