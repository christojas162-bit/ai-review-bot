import sqlite3
import csv
import os
from datetime import datetime
from pathlib import Path
from config import Config

def get_db_path():
    path_str = os.getenv("DATABASE_PATH") or Config.DATABASE_PATH
    db_path = Path(path_str)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)

def get_db_connection():
    conn = sqlite3.connect(get_db_path(), timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=20000")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(seed_sample=True):
    """Initializes tables and optionally seeds sample data if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Candidates table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        assigned_task TEXT,
        task_requirements TEXT,
        start_date TEXT,
        deadline TEXT,
        review_date TEXT,
        review_time TEXT,
        submission_link TEXT,
        submission_description TEXT,
        completed_items TEXT,
        missing_items TEXT,
        improvement_suggestions TEXT,
        next_review_date TEXT,
        next_review_time TEXT,
        status TEXT NOT NULL DEFAULT 'Draft',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    ''')

    # Reviews table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id TEXT NOT NULL,
        review_round INTEGER NOT NULL DEFAULT 1,
        submission_link TEXT,
        submission_description TEXT,
        original_requirements TEXT,
        task_summary TEXT,
        completed_requirements TEXT,
        missing_requirements TEXT,
        potential_issues TEXT,
        enhancements TEXT,
        recommended_actions TEXT,
        suggested_status TEXT,
        final_status TEXT,
        reviewer_notes TEXT,
        is_ai_generated INTEGER DEFAULT 1,
        ai_provider TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id)
    )
    ''')

    # Notifications Log table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id TEXT NOT NULL,
        recipient_email TEXT NOT NULL,
        notification_type TEXT NOT NULL,
        subject TEXT NOT NULL,
        body_html TEXT NOT NULL,
        body_text TEXT NOT NULL,
        status TEXT NOT NULL,
        error_message TEXT,
        is_duplicate_blocked INTEGER DEFAULT 0,
        sent_at TEXT,
        created_at TEXT NOT NULL
    )
    ''')

    # AI Explanations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ai_explanations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id TEXT NOT NULL,
        task_title TEXT NOT NULL,
        objective TEXT,
        required_modules TEXT,
        step_by_step_plan TEXT,
        expected_output TEXT,
        deliverables TEXT,
        deadline TEXT,
        review_requirements TEXT,
        raw_content TEXT,
        is_approved INTEGER DEFAULT 0,
        approved_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id)
    )
    ''')

    # Settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS integration_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT,
        updated_at TEXT NOT NULL
    )
    ''')

    # Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_candidates_deadline ON candidates(deadline)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reviews_candidate ON reviews(candidate_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notif_candidate_type ON notifications_log(candidate_id, notification_type)')

    conn.commit()

    # Check if we should seed sample data
    if seed_sample:
        cursor.execute('SELECT COUNT(*) as cnt FROM candidates')
        cnt = cursor.fetchone()['cnt']
        if cnt == 0:
            sample_csv = Config.BASE_DIR / "data" / "sample_candidates.csv"
            if sample_csv.exists():
                seed_from_csv(sample_csv)

    conn.close()

def seed_from_csv(csv_path):
    """Loads sample data from CSV file into SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("Candidate ID", "").strip()
            if not cid:
                continue
            cursor.execute('''
            INSERT OR IGNORE INTO candidates (
                candidate_id, name, email, assigned_task, task_requirements,
                start_date, deadline, review_date, review_time, submission_link,
                completed_items, missing_items, improvement_suggestions,
                next_review_date, next_review_time, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                cid,
                row.get("Name", "").strip(),
                row.get("Email", "").strip(),
                row.get("Assigned Task", "").strip(),
                row.get("Task Requirements", "").strip(),
                row.get("Start Date", "").strip(),
                row.get("Deadline", "").strip(),
                row.get("Review Date", "").strip(),
                row.get("Review Time", "").strip(),
                row.get("Submission Link", "").strip(),
                row.get("Completed Items", "").strip(),
                row.get("Missing Items", "").strip(),
                row.get("Improvement Suggestions", "").strip(),
                row.get("Next Review Date", "").strip(),
                row.get("Next Review Time", "").strip(),
                row.get("Status", "Draft").strip() or "Draft",
                now_str,
                now_str
            ))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# Candidate Operations
# ---------------------------------------------------------

VALID_STATUSES = [
    "Draft",
    "Ready for Assignment",
    "Assigned",
    "In Progress",
    "Ready for Review",
    "Revision Required",
    "Completed"
]

def get_all_candidates(search=None, status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM candidates WHERE 1=1"
    params = []

    if search:
        search_param = f"%{search.strip()}%"
        query += " AND (candidate_id LIKE ? OR name LIKE ? OR email LIKE ? OR assigned_task LIKE ?)"
        params.extend([search_param, search_param, search_param, search_param])

    if status and status != "All":
        query += " AND status = ?"
        params.append(status.strip())

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_candidate_by_id(candidate_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_candidate(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cid = data.get("candidate_id", "").strip()
    if not cid:
        cursor.execute("SELECT COUNT(*) as cnt FROM candidates")
        cnt = cursor.fetchone()['cnt']
        cid = f"CAN-{1000 + cnt + 1}"

    status = data.get("status", "Draft")
    if status not in VALID_STATUSES:
        status = "Draft"

    cursor.execute('''
    INSERT INTO candidates (
        candidate_id, name, email, assigned_task, task_requirements,
        start_date, deadline, review_date, review_time, submission_link,
        submission_description, completed_items, missing_items,
        improvement_suggestions, next_review_date, next_review_time,
        status, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        cid,
        data.get("name", "").strip(),
        data.get("email", "").strip(),
        data.get("assigned_task", "").strip(),
        data.get("task_requirements", "").strip(),
        data.get("start_date", "").strip(),
        data.get("deadline", "").strip(),
        data.get("review_date", "").strip(),
        data.get("review_time", "").strip(),
        data.get("submission_link", "").strip(),
        data.get("submission_description", "").strip(),
        data.get("completed_items", "").strip(),
        data.get("missing_items", "").strip(),
        data.get("improvement_suggestions", "").strip(),
        data.get("next_review_date", "").strip(),
        data.get("next_review_time", "").strip(),
        status,
        now_str,
        now_str
    ))
    conn.commit()
    conn.close()
    return get_candidate_by_id(cid)

def update_candidate(candidate_id, data):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    allowed_fields = [
        "name", "email", "assigned_task", "task_requirements",
        "start_date", "deadline", "review_date", "review_time",
        "submission_link", "submission_description", "completed_items",
        "missing_items", "improvement_suggestions", "next_review_date",
        "next_review_time", "status"
    ]
    set_clauses = []
    params = []

    for f in allowed_fields:
        if f in data:
            val = data[f]
            if f == "status" and val not in VALID_STATUSES:
                continue
            set_clauses.append(f"{f} = ?")
            params.append(val.strip() if isinstance(val, str) else val)

    if not set_clauses:
        conn.close()
        return get_candidate_by_id(candidate_id)

    set_clauses.append("updated_at = ?")
    params.append(now_str)
    params.append(candidate_id)

    sql = f"UPDATE candidates SET {', '.join(set_clauses)} WHERE candidate_id = ?"
    cursor.execute(sql, params)
    conn.commit()
    conn.close()
    return get_candidate_by_id(candidate_id)

def delete_candidate(candidate_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candidates WHERE candidate_id = ?", (candidate_id,))
    cursor.execute("DELETE FROM reviews WHERE candidate_id = ?", (candidate_id,))
    cursor.execute("DELETE FROM notifications_log WHERE candidate_id = ?", (candidate_id,))
    cursor.execute("DELETE FROM ai_explanations WHERE candidate_id = ?", (candidate_id,))
    conn.commit()
    conn.close()
    return True

def upsert_candidate_from_sheet(record):
    """Safe upsert matching on candidate_id."""
    cid = record.get("candidate_id", "").strip()
    if not cid:
        return False, "Missing candidate_id"
    
    existing = get_candidate_by_id(cid)
    if existing:
        update_candidate(cid, record)
        return True, "Updated"
    else:
        create_candidate(record)
        return True, "Inserted"

def get_dashboard_metrics():
    """Computes real-time recruitment metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates")
    candidates = [dict(row) for row in cursor.fetchall()]
    conn.close()

    total_candidates = len(candidates)
    assigned_tasks = 0
    in_progress = 0
    pending_reviews = 0
    completed_tasks = 0
    overdue_tasks = 0
    upcoming_reviews = 0

    today_str = datetime.now().strftime("%Y-%m-%d")

    for c in candidates:
        status = c.get("status")
        deadline = c.get("deadline") or ""
        rev_date = c.get("review_date") or c.get("next_review_date") or ""

        if status in ["Assigned", "In Progress", "Ready for Review", "Revision Required", "Completed"]:
            assigned_tasks += 1
        
        if status == "In Progress":
            in_progress += 1

        if status in ["Ready for Review", "Revision Required"]:
            pending_reviews += 1

        if status == "Completed":
            completed_tasks += 1

        # Check overdue
        if status not in ["Completed", "Draft"] and deadline:
            if deadline < today_str:
                overdue_tasks += 1

        # Upcoming reviews (scheduled for today or future, not completed)
        if status not in ["Completed", "Draft"] and rev_date:
            if rev_date >= today_str:
                upcoming_reviews += 1

    return {
        "total_candidates": total_candidates,
        "assigned_tasks": assigned_tasks,
        "in_progress": in_progress,
        "pending_reviews": pending_reviews,
        "upcoming_reviews": upcoming_reviews,
        "overdue_tasks": overdue_tasks,
        "completed_tasks": completed_tasks
    }

# ---------------------------------------------------------
# Reviews Operations
# ---------------------------------------------------------

def create_review(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Determine round
    cid = data.get("candidate_id")
    cursor.execute("SELECT COUNT(*) as cnt FROM reviews WHERE candidate_id = ?", (cid,))
    round_num = cursor.fetchone()['cnt'] + 1

    cursor.execute('''
    INSERT INTO reviews (
        candidate_id, review_round, submission_link, submission_description,
        original_requirements, task_summary, completed_requirements,
        missing_requirements, potential_issues, enhancements,
        recommended_actions, suggested_status, final_status, reviewer_notes,
        is_ai_generated, ai_provider, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        cid,
        round_num,
        data.get("submission_link", ""),
        data.get("submission_description", ""),
        data.get("original_requirements", ""),
        data.get("task_summary", ""),
        data.get("completed_requirements", ""),
        data.get("missing_requirements", ""),
        data.get("potential_issues", ""),
        data.get("enhancements", ""),
        data.get("recommended_actions", ""),
        data.get("suggested_status", ""),
        data.get("final_status", data.get("suggested_status", "")),
        data.get("reviewer_notes", ""),
        1 if data.get("is_ai_generated", True) else 0,
        data.get("ai_provider", "demo"),
        now_str
    ))
    review_id = cursor.lastrowid
    conn.commit()

    # Update candidate fields
    cand_update = {
        "status": data.get("final_status", data.get("suggested_status", "")),
        "completed_items": data.get("completed_requirements", ""),
        "missing_items": data.get("missing_requirements", ""),
        "improvement_suggestions": data.get("enhancements", "")
    }
    if data.get("next_review_date"):
        cand_update["next_review_date"] = data.get("next_review_date")
    if data.get("next_review_time"):
        cand_update["next_review_time"] = data.get("next_review_time")
    if data.get("submission_link"):
        cand_update["submission_link"] = data.get("submission_link")

    conn.close()
    update_candidate(cid, cand_update)
    return get_review_by_id(review_id)

def get_review_by_id(review_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_reviews_by_candidate(candidate_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews WHERE candidate_id = ? ORDER BY id DESC", (candidate_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_all_reviews(limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT r.*, c.name as candidate_name, c.email as candidate_email, c.assigned_task as task_title
    FROM reviews r
    LEFT JOIN candidates c ON r.candidate_id = c.candidate_id
    ORDER BY r.id DESC LIMIT ?
    ''', (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

# ---------------------------------------------------------
# Notifications Operations
# ---------------------------------------------------------

def log_notification(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
    INSERT INTO notifications_log (
        candidate_id, recipient_email, notification_type, subject,
        body_html, body_text, status, error_message, is_duplicate_blocked,
        sent_at, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get("candidate_id"),
        data.get("recipient_email"),
        data.get("notification_type"),
        data.get("subject"),
        data.get("body_html", ""),
        data.get("body_text", ""),
        data.get("status", "PREVIEW"),
        data.get("error_message", None),
        1 if data.get("is_duplicate_blocked") else 0,
        now_str if data.get("status") in ("SENT", "SIMULATED_SENT") else None,
        now_str
    ))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id

def get_notifications(limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT n.*, c.name as candidate_name 
    FROM notifications_log n
    LEFT JOIN candidates c ON n.candidate_id = c.candidate_id
    ORDER BY n.id DESC LIMIT ?
    ''', (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def has_notification_been_sent_recently(candidate_id, notification_type, within_hours=12):
    """Prevents duplicate reminder spam."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if a non-failed notification was sent in the last N hours
    cursor.execute('''
    SELECT sent_at FROM notifications_log
    WHERE candidate_id = ? AND notification_type = ?
    AND status IN ('SENT', 'SIMULATED_SENT')
    ORDER BY id DESC LIMIT 1
    ''', (candidate_id, notification_type))
    row = cursor.fetchone()
    conn.close()
    if not row or not row['sent_at']:
        return False

    try:
        sent_time = datetime.strptime(row['sent_at'], "%Y-%m-%d %H:%M:%S")
        elapsed_hours = (datetime.now() - sent_time).total_seconds() / 3600.0
        return elapsed_hours < within_hours
    except Exception:
        return False

# ---------------------------------------------------------
# AI Explanation Operations
# ---------------------------------------------------------

def save_ai_explanation(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Replace previous explanation for candidate
    cursor.execute("DELETE FROM ai_explanations WHERE candidate_id = ?", (data.get("candidate_id"),))

    cursor.execute('''
    INSERT INTO ai_explanations (
        candidate_id, task_title, objective, required_modules,
        step_by_step_plan, expected_output, deliverables, deadline,
        review_requirements, raw_content, is_approved, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get("candidate_id"),
        data.get("task_title", ""),
        data.get("objective", ""),
        data.get("required_modules", ""),
        data.get("step_by_step_plan", ""),
        data.get("expected_output", ""),
        data.get("deliverables", ""),
        data.get("deadline", ""),
        data.get("review_requirements", ""),
        data.get("raw_content", ""),
        0,
        now_str
    ))
    exp_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_ai_explanation(data.get("candidate_id"))

def get_ai_explanation(candidate_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_explanations WHERE candidate_id = ? ORDER BY id DESC LIMIT 1", (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def approve_ai_explanation(candidate_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
    UPDATE ai_explanations SET is_approved = 1, approved_at = ? WHERE candidate_id = ?
    ''', (now_str, candidate_id))
    conn.commit()
    conn.close()
    return True

# ---------------------------------------------------------
# Integration Settings Operations
# ---------------------------------------------------------

def get_setting(key, default=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM integration_settings WHERE setting_key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row['setting_value'] if row else default
    except Exception:
        return default

def set_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
    INSERT INTO integration_settings (setting_key, setting_value, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value, updated_at = excluded.updated_at
    ''', (key, str(value), now_str))
    conn.commit()
    conn.close()
    return True

def get_all_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM integration_settings")
    rows = {r['setting_key']: r['setting_value'] for r in cursor.fetchall()}
    conn.close()
    return rows
