# AI Recruitment & Internship Task Allocation and Review Bot

A full-stack, enterprise-grade AI automation web application engineered with **Flask**, **SQLite**, **APScheduler**, and modern responsive web technologies. It automates candidate tracking, technical task allocation, AI-powered task breakdown and roadmapping, submission verification, follow-up evaluation cycles, and deadline reminders with full Google Sheets API and SMTP integration.

---

## 🌟 Key Capabilities & Features

### 1. Dashboard Overview
- Real-time recruitment KPI cards:
  - **Total Candidates**
  - **Assigned Tasks**
  - **Tasks in Progress**
  - **Pending Reviews**
  - **Upcoming Reviews**
  - **Overdue Tasks**
  - **Completed Tasks**
- System health and integration indicator badges (AI engine, Email dispatch mode, Google Sheets connection status, and APScheduler daemon).
- Quick-action shortcuts and recent candidate evaluation pipeline.

### 2. Candidate & Task Management
- Add, search, filter, view, edit, and delete candidate records.
- Track status across the lifecycle: `Draft` ➔ `Ready for Assignment` ➔ `Assigned` ➔ `In Progress` ➔ `Ready for Review` ➔ `Revision Required` ➔ `Completed`.
- Required-field validation on candidate ID, name, email, task specifications, and dates.

### 3. Google Sheets Integration & CSV Fallback
- Spreadsheet Name: **AI Recruitment & Internship Task Review Bot**
- Synchronizes all 16 standardized columns:
  `Candidate ID`, `Name`, `Email`, `Assigned Task`, `Task Requirements`, `Start Date`, `Deadline`, `Review Date`, `Review Time`, `Submission Link`, `Completed Items`, `Missing Items`, `Improvement Suggestions`, `Next Review Date`, `Next Review Time`, `Status`.
- **Immediate CSV Fallback:** Upload or paste CSV records with candidate matching and safe upsert (updates existing records without losing review history).
- **One-Click CSV Export:** Export current database records formatted identically to Google Sheets.
- **Service Account Sync:** Direct sync with Google Sheets API when `credentials.json` and Spreadsheet ID are configured.

### 4. AI Task Explanation Module
- Triggered when tasks are marked `Ready for Assignment` (or on demand for any candidate).
- Synthesizes structured breakdowns:
  - **Task Objective**
  - **Required Modules**
  - **Step-by-Step Implementation Roadmap**
  - **Expected Output**
  - **Deliverables & Repository Requirements**
  - **Deadline & Review Criteria**
- Human recruiter approval gate before any email is dispatched.
- Prevents duplicate assignment emails.

### 5. AI Submission Review & Follow-up Cycle
- Submissions can be analyzed via repository link (GitHub/GitLab/Drive) and candidate description.
- **URL Reachability Verification:** Checks if the repository URL is reachable (HTTP 200). If unreachable or private, explicitly flags the limitation and evaluates based on candidate notes.
- Generates 7 structured assessment dimensions:
  1. Task Summary
  2. Completed / Satisfied Requirements
  3. Missing / Outstanding Criteria
  4. Potential Issues & Bugs
  5. Suggested Enhancements
  6. Recommended Next Actions
  7. Suggested Review Status (`Revision Required`, `In Progress`, `Ready for Review`, `Completed`)
- **Reviewer Sign-off:** Human reviewer can edit feedback, calibrate final status, and set next review date/time before saving.
- **Cycle Repeat & Auto-Stop:** Incomplete tasks schedule next check-in reminders. Tasks marked `Completed` stop all future reminder automation.

### 6. Email Automation & Safe Demo Mode
- Templates for: `TASK_ASSIGNMENT`, `DEADLINE_REMINDER`, `REVIEW_REMINDER`, and `FEEDBACK`.
- **Safe Demo Mode:** When SMTP credentials are unconfigured or unconfirmed, notifications are logged as `SIMULATED_SENT` in the Notification Audit Trail without hitting real mailboxes.
- **Explicit Confirmation:** Real SMTP dispatch requires entering valid credentials and checking the confirmation toggle.
- **Duplicate Prevention:** Automatically blocks duplicate reminder emails sent to the same candidate within a 12-hour window.
- **Completed Protection:** Reminders are strictly suppressed for `Completed` tasks.

### 7. Background APScheduler Daemon
- Runs scheduled background jobs in the configured local timezone (`Asia/Kolkata` or local system timezone).
- Automated scans every 15 minutes checking approaching deadlines and due review dates.
- Manual trigger button (**Run Reminder Check Now**) with instant diagnostic reports.

---

## 🛠️ Project Structure

```
ai-recruitment-task-bot/
├── app.py                     # Main Flask application & REST API routes
├── config.py                  # Environment & timezone configuration
├── database.py                # SQLite schema, migrations, CRUD, and metrics logic
├── requirements.txt           # Python dependencies
├── .env.example               # Configuration template
├── .env                       # Active runtime environment configuration
├── README.md                  # Comprehensive documentation & setup guide
├── services/
│   ├── __init__.py
│   ├── ai_service.py          # AI logic (Gemini, OpenAI, URL inspector, Demo Simulator)
│   ├── email_service.py       # Email generator, validator, SMTP sender, Demo logger
│   ├── sheets_service.py      # Google Sheets API client & CSV import/export
│   └── scheduler_service.py   # APScheduler background automation & duplicate guard
├── static/
│   ├── css/
│   │   └── style.css          # Responsive recruiter UI design
│   └── js/
│       └── app.js             # SPA dynamic controller, modals, AJAX operations, toasts
├── templates/
│   └── index.html             # Single-page dashboard containing all 9 sections
├── data/
│   ├── sample_candidates.csv  # Fictional candidate records for demo seeding
│   └── recruitment_bot.db     # SQLite database (auto-created on first run)
└── tests/
    ├── __init__.py
    ├── test_database.py       # Unit tests for database CRUD and queries
    ├── test_ai_service.py     # Unit tests for AI explainer & reviewer
    ├── test_email_service.py  # Unit tests for email generation & duplicate guard
    ├── test_sheets_service.py # Unit tests for CSV import/export & matching
    └── test_routes.py         # End-to-end integration tests for Flask endpoints
```

---

## 🚀 Quickstart & Execution Guide

### Prerequisites
- Python 3.10+ installed
- Terminal / PowerShell in VS Code

### Step 1: Open the Project in VS Code
Open the project directory:
```powershell
code "C:\Users\antow\.gemini\antigravity\scratch\ai-recruitment-task-bot"
```
Or open the integrated terminal in VS Code (`Ctrl + ~`) and navigate to the folder:
```powershell
Set-Location "C:\Users\antow\.gemini\antigravity\scratch\ai-recruitment-task-bot"
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run the Automated Test Suite
Verify that all 22 test cases pass:
```powershell
python -m unittest discover tests
```

### Step 4: Launch the Web Application
```powershell
python app.py
```

### Step 5: Open the Dashboard in your Browser
Open your browser to:
[http://127.0.0.1:5000](http://127.0.0.1:5000)

The application will launch in **Safe Demo Mode** pre-seeded with realistic candidate records across all lifecycle stages.

---

## ⚙️ External Integration Setup

### A. Google Sheets API Configuration
1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `Recruitment-Task-Bot`).
3. Navigate to **APIs & Services ➔ Library** and enable **Google Sheets API**.
4. Navigate to **APIs & Services ➔ Credentials** ➔ click **Create Credentials ➔ Service Account**.
5. After creating the service account, go to its **Keys** tab, click **Add Key ➔ Create new key ➔ JSON**.
6. Save the downloaded JSON file as `credentials.json` in the root directory:
   `ai-recruitment-task-bot/credentials.json`
7. Create a Google Spreadsheet titled **AI Recruitment & Internship Task Review Bot**.
8. Share the Google Sheet with the `client_email` address found inside your `credentials.json` file as an **Editor**.
9. Copy the Spreadsheet ID from the URL (`https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`) and paste it into the **Integration Settings** panel or in `.env`:
   ```env
   GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
   ```
10. Click **Sync Google Sheets Now** in the dashboard.

### B. AI Engine Configuration (Gemini / OpenAI)
In `.env` or in the **Integration Settings** tab:
- **Demo Mode (Default):**
  ```env
  AI_PROVIDER=demo
  AI_API_KEY=
  ```
  Generates detailed, realistic task breakdowns and reviews using built-in heuristic analysis with explicit `[DEMO SIMULATION]` disclosures.

- **Google Gemini API:**
  ```env
  AI_PROVIDER=gemini
  AI_API_KEY=your_gemini_api_key_here
  AI_MODEL=gemini-1.5-flash
  ```

- **OpenAI API:**
  ```env
  AI_PROVIDER=openai
  AI_API_KEY=your_openai_api_key_here
  AI_MODEL=gpt-4o-mini
  ```

### C. Email & SMTP Configuration
- **Safe Demo Mode (Default):**
  ```env
  EMAIL_MODE=demo
  ```
  All outbound notifications are captured in **Email Preview & Notification Logs** without sending real emails.

- **Production SMTP (Gmail / Custom SMTP):**
  ```env
  EMAIL_MODE=smtp
  SMTP_SERVER=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USE_TLS=true
  SMTP_USERNAME=your_email@gmail.com
  SMTP_PASSWORD=your_google_app_password
  EMAIL_FROM=your_email@gmail.com
  ```
  *(For Gmail, use a 16-character [Google App Password](https://myaccount.google.com/apppasswords), not your regular password).*

---

## 🔒 Security & Reliability Guarantees
- **No Hardcoded Secrets:** All secrets reside in `.env` (gitignored).
- **Parameterized SQL:** All SQLite database queries use parameterized placeholders (`?`) preventing SQL injection.
- **URL Reachability Guard:** Safe timeouts (4s) on submission URL inspections to prevent hanging or SSRF attacks.
- **Duplicate Prevention:** Background scheduler and manual triggers enforce a 12-hour quiet window per candidate notification type.
- **Zero Accidental Sends:** Real emails require both configured SMTP credentials and explicit user confirmation.
