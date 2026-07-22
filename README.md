# Smart Study Reminder AI

An intelligent, data-grounded study planner and reminder system built for the ByteXL × AMD Mini Hackathon. It features dynamic priority calculation, automated document import processing, rule-based intent routing, and timezone-robust OTP verification.

---

## 🛠 Tech Stack

* **Backend**: FastAPI (Python 3.11+), SQLite (SQLAlchemy ORM), APScheduler, Uvicorn, pdfplumber, pytesseract.
* **Frontend**: React (Vite, TypeScript, TailwindCSS/Vanilla HSL CSS tokens), TanStack Query, Framer Motion, Recharts.
* **AI Engine**: Local fallback matching and remote AMD JupyterLab endpoints.

---

## 📧 Real SMTP & Gmail Setup (Security & Best Practices)

Smart Study Reminder AI supports real email delivery for password resets and verification OTPs.

### Gmail SMTP Configuration Requirements

If using Gmail as your SMTP provider, follow these critical steps:

1. **Enable 2-Step Verification**: You must turn on 2-Step Verification in your Google Account security settings.
2. **Generate an App Password**:
   - Navigate to Google Account Settings → Security → 2-Step Verification (scroll to the bottom).
   - Under **App passwords**, select **Other (custom name)** and enter `Smart Study AI`.
   - Click **Generate** and copy the 16-character code.
3. **Environment Configuration**:
   - Paste the 16-character app password into `SMTP_PASSWORD` in your local `.env` file (which is gitignored).
   - Do **NOT** use your main Google account password; only the generated App Password is supported.

### 🛡 Security Notice
* **Never commit credentials**: App Passwords, API tokens, and credentials must **NEVER** appear in code, logs, prompts, or committed files.
* **Only use environment variables**: Real credentials must live in the gitignored `.env` file. Only placeholder variable names should be present in `.env.example` or documentation.

---

## 🚀 Getting Started

### 1. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate   # Windows
# or: source venv/bin/activate (Linux/Mac)
pip install -r requirements.txt
cp .env.example .env      # Add your private configs here
python app/main.py        # Runs on http://localhost:8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev               # Runs on http://localhost:5173
```
