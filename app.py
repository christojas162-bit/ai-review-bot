import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response
from config import Config
import database
from services.ai_service import AIService
from services.email_service import EmailService
from services.sheets_service import SheetsService
from services.scheduler_service import SchedulerService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("recruitment_bot")

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY

# Ensure DB initialized on startup
with app.app_context():
    database.init_db(seed_sample=True)
    if Config.ENABLE_SCHEDULER and not os.getenv("TESTING"):
        SchedulerService.init_scheduler(app)

# -----------------------------------------------------------------------------
# Frontend Routes
# -----------------------------------------------------------------------------

@app.route("/")
def index():
    """Renders the main single-page recruiter dashboard."""
    metrics = database.get_dashboard_metrics()
    return render_template("index.html", metrics=metrics, timezone=Config.TIMEZONE_STR)

# -----------------------------------------------------------------------------
# 1. Dashboard Overview APIs
# -----------------------------------------------------------------------------

@app.route("/api/metrics", methods=["GET"])
def api_metrics():
    metrics = database.get_dashboard_metrics()
    return jsonify({"success": True, "data": metrics})

# -----------------------------------------------------------------------------
# 2. Candidate Management APIs
# -----------------------------------------------------------------------------

@app.route("/api/candidates", methods=["GET"])
def api_get_candidates():
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    candidates = database.get_all_candidates(search=search, status=status)
    return jsonify({"success": True, "count": len(candidates), "data": candidates})

@app.route("/api/candidates/<candidate_id>", methods=["GET"])
def api_get_candidate(candidate_id):
    c = database.get_candidate_by_id(candidate_id)
    if not c:
        return jsonify({"success": False, "error": f"Candidate '{candidate_id}' not found."}), 404
    reviews = database.get_reviews_by_candidate(candidate_id)
    explanation = database.get_ai_explanation(candidate_id)
    return jsonify({
        "success": True,
        "data": c,
        "reviews": reviews,
        "explanation": explanation
    })

@app.route("/api/candidates", methods=["POST"])
def api_create_candidate():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()

    if not name:
        return jsonify({"success": False, "error": "Candidate Name is required."}), 400
    if not email:
        return jsonify({"success": False, "error": "Candidate Email is required."}), 400

    cand = database.create_candidate(data)
    return jsonify({"success": True, "message": f"Candidate {cand['candidate_id']} created.", "data": cand}), 201

@app.route("/api/candidates/<candidate_id>", methods=["PUT"])
def api_update_candidate(candidate_id):
    existing = database.get_candidate_by_id(candidate_id)
    if not existing:
        return jsonify({"success": False, "error": f"Candidate '{candidate_id}' not found."}), 404

    data = request.get_json() or {}
    updated = database.update_candidate(candidate_id, data)
    return jsonify({"success": True, "message": f"Candidate {candidate_id} updated.", "data": updated})

@app.route("/api/candidates/<candidate_id>", methods=["DELETE"])
def api_delete_candidate(candidate_id):
    existing = database.get_candidate_by_id(candidate_id)
    if not existing:
        return jsonify({"success": False, "error": f"Candidate '{candidate_id}' not found."}), 404

    database.delete_candidate(candidate_id)
    return jsonify({"success": True, "message": f"Candidate {candidate_id} and associated history deleted."})

# -----------------------------------------------------------------------------
# 3. Task Allocation APIs
# -----------------------------------------------------------------------------

@app.route("/api/candidates/<candidate_id>/allocate-task", methods=["POST"])
def api_allocate_task(candidate_id):
    existing = database.get_candidate_by_id(candidate_id)
    if not existing:
        return jsonify({"success": False, "error": f"Candidate '{candidate_id}' not found."}), 404

    data = request.get_json() or {}
    task = (data.get("assigned_task") or "").strip()
    reqs = (data.get("task_requirements") or "").strip()
    start_date = (data.get("start_date") or "").strip()
    deadline = (data.get("deadline") or "").strip()
    review_date = (data.get("review_date") or "").strip()
    review_time = (data.get("review_time") or "").strip()
    target_status = data.get("status", "Ready for Assignment")

    # Required field validation
    missing = []
    if not task: missing.append("Assigned Task Title")
    if not reqs: missing.append("Task Requirements")
    if not start_date: missing.append("Start Date")
    if not deadline: missing.append("Deadline")
    if not review_date: missing.append("Review Date")
    if not review_time: missing.append("Review Time")

    if missing:
        return jsonify({
            "success": False,
            "error": f"Validation failed. Missing required fields: {', '.join(missing)}"
        }), 400

    update_payload = {
        "assigned_task": task,
        "task_requirements": reqs,
        "start_date": start_date,
        "deadline": deadline,
        "review_date": review_date,
        "review_time": review_time,
        "next_review_date": review_date,
        "next_review_time": review_time,
        "status": target_status
    }
    updated = database.update_candidate(candidate_id, update_payload)
    return jsonify({
        "success": True,
        "message": f"Task '{task}' allocated to {candidate_id}. Status marked as '{target_status}'.",
        "data": updated
    })

# -----------------------------------------------------------------------------
# 4. AI Task Explanation APIs
# -----------------------------------------------------------------------------

@app.route("/api/candidates/<candidate_id>/ai-explanation/generate", methods=["POST"])
def api_generate_explanation(candidate_id):
    c = database.get_candidate_by_id(candidate_id)
    if not c:
        return jsonify({"success": False, "error": f"Candidate '{candidate_id}' not found."}), 404

    if not c.get("assigned_task"):
        return jsonify({"success": False, "error": "Candidate has no assigned task to explain."}), 400

    explanation = AIService.generate_task_explanation(c)
    explanation["candidate_id"] = candidate_id
    saved = database.save_ai_explanation(explanation)
    return jsonify({
        "success": True,
        "message": "AI Task Explanation generated successfully.",
        "data": saved
    })

@app.route("/api/candidates/<candidate_id>/ai-explanation/approve-and-send", methods=["POST"])
def api_approve_and_send_explanation(candidate_id):
    c = database.get_candidate_by_id(candidate_id)
    if not c:
        return jsonify({"success": False, "error": f"Candidate '{candidate_id}' not found."}), 404

    explanation = database.get_ai_explanation(candidate_id)
    if not explanation:
        return jsonify({"success": False, "error": "No explanation found. Please generate explanation first."}), 400

    data = request.get_json() or {}
    confirm_real = bool(data.get("confirm_real_send", False))

    # Approve explanation
    database.approve_ai_explanation(candidate_id)

    # Dispatch assignment email (or demo simulated notification)
    send_result = EmailService.send_notification(
        c,
        notification_type="TASK_ASSIGNMENT",
        extra_data={"explanation": explanation},
        is_confirmed_real=confirm_real
    )

    # Update candidate status to Assigned
    database.update_candidate(candidate_id, {"status": "Assigned"})

    return jsonify({
        "success": True,
        "message": f"Task assignment approved. Notification: {send_result.get('message')}",
        "notification_result": send_result,
        "new_status": "Assigned"
    })

# -----------------------------------------------------------------------------
# 5. AI Submission Review APIs
# -----------------------------------------------------------------------------

@app.route("/api/candidates/<candidate_id>/ai-review/generate", methods=["POST"])
def api_generate_review(candidate_id):
    c = database.get_candidate_by_id(candidate_id)
    if not c:
        return jsonify({"success": False, "error": f"Candidate '{candidate_id}' not found."}), 404

    data = request.get_json() or {}
    link = (data.get("submission_link") or c.get("submission_link") or "").strip()
    desc = (data.get("submission_description") or c.get("submission_description") or "").strip()
    notes = (data.get("reviewer_notes") or "").strip()

    review_draft = AIService.review_submission(
        candidate=c,
        submission_link=link,
        submission_desc=desc,
        reviewer_notes=notes
    )

    review_draft["candidate_id"] = candidate_id
    review_draft["submission_link"] = link
    review_draft["submission_description"] = desc
    review_draft["reviewer_notes"] = notes
    review_draft["original_requirements"] = c.get("task_requirements", "")

    return jsonify({
        "success": True,
        "message": "AI submission analysis completed.",
        "data": review_draft
    })

@app.route("/api/candidates/<candidate_id>/ai-review/save", methods=["POST"])
def api_save_review(candidate_id):
    c = database.get_candidate_by_id(candidate_id)
    if not c:
        return jsonify({"success": False, "error": f"Candidate '{candidate_id}' not found."}), 404

    data = request.get_json() or {}
    final_status = data.get("final_status") or data.get("suggested_status") or "Revision Required"

    review_record = database.create_review(data)

    # If reviewer opted to dispatch feedback email
    send_feedback = data.get("send_feedback_email", False)
    email_result = None
    if send_feedback:
        email_result = EmailService.send_notification(
            candidate=c,
            notification_type="FEEDBACK",
            extra_data={
                "status": final_status,
                "summary": data.get("task_summary"),
                "completed": data.get("completed_requirements"),
                "missing": data.get("missing_requirements"),
                "enhancements": data.get("enhancements"),
                "next_review_date": data.get("next_review_date"),
                "next_review_time": data.get("next_review_time")
            },
            is_confirmed_real=bool(data.get("confirm_real_send", False))
        )

    return jsonify({
        "success": True,
        "message": f"Review saved successfully. Candidate status updated to '{final_status}'.",
        "data": review_record,
        "email_result": email_result
    })

# -----------------------------------------------------------------------------
# 6. Review Schedule and Reminders APIs
# -----------------------------------------------------------------------------

@app.route("/api/scheduler/status", methods=["GET"])
def api_scheduler_status():
    status = SchedulerService.get_status()
    return jsonify({"success": True, "data": status})

@app.route("/api/scheduler/trigger-check", methods=["POST"])
def api_trigger_reminder_check():
    result = SchedulerService.run_reminder_check()
    return jsonify({
        "success": True,
        "message": "Manual reminder scan completed.",
        "result": result
    })

@app.route("/api/reminders/upcoming", methods=["GET"])
def api_upcoming_reminders():
    candidates = database.get_all_candidates()
    now_str = datetime.now().strftime("%Y-%m-%d")
    upcoming = []

    for c in candidates:
        if c.get("status") in ("Completed", "Draft"):
            continue
        deadline = c.get("deadline") or ""
        rev_date = c.get("review_date") or c.get("next_review_date") or ""

        is_overdue = deadline and deadline < now_str
        is_upcoming_review = rev_date and rev_date >= now_str
        is_upcoming_deadline = deadline and deadline >= now_str

        if is_overdue or is_upcoming_review or is_upcoming_deadline:
            upcoming.append({
                "candidate_id": c["candidate_id"],
                "name": c["name"],
                "email": c["email"],
                "assigned_task": c["assigned_task"],
                "deadline": deadline,
                "review_date": rev_date,
                "review_time": c.get("review_time") or c.get("next_review_time") or "",
                "status": c["status"],
                "is_overdue": bool(is_overdue)
            })

    return jsonify({"success": True, "count": len(upcoming), "data": upcoming})

# -----------------------------------------------------------------------------
# 7. Email Preview & Notification Logs APIs
# -----------------------------------------------------------------------------

@app.route("/api/notifications/preview", methods=["POST"])
def api_preview_notification():
    data = request.get_json() or {}
    cid = data.get("candidate_id")
    c = database.get_candidate_by_id(cid) if cid else None
    if not c:
        return jsonify({"success": False, "error": f"Candidate '{cid}' not found."}), 404

    notif_type = data.get("notification_type", "TASK_ASSIGNMENT")
    extra = data.get("extra_data", {})
    preview_data = EmailService.preview(notif_type, c, extra)
    return jsonify({"success": True, "data": preview_data})

@app.route("/api/notifications/send", methods=["POST"])
def api_send_notification():
    data = request.get_json() or {}
    cid = data.get("candidate_id")
    c = database.get_candidate_by_id(cid) if cid else None
    if not c:
        return jsonify({"success": False, "error": f"Candidate '{cid}' not found."}), 404

    notif_type = data.get("notification_type", "TASK_ASSIGNMENT")
    confirm_real = bool(data.get("confirm_real_send", False))
    extra = data.get("extra_data", {})

    result = EmailService.send_notification(c, notif_type, extra, is_confirmed_real=confirm_real)
    return jsonify({"success": result.get("success", False), "result": result})

@app.route("/api/notifications", methods=["GET"])
def api_get_notifications():
    limit = int(request.args.get("limit", 100))
    logs = database.get_notifications(limit=limit)
    return jsonify({"success": True, "count": len(logs), "data": logs})

# -----------------------------------------------------------------------------
# 8. Review History APIs
# -----------------------------------------------------------------------------

@app.route("/api/reviews", methods=["GET"])
def api_get_reviews():
    cid = request.args.get("candidate_id")
    if cid:
        reviews = database.get_reviews_by_candidate(cid)
    else:
        reviews = database.get_all_reviews()
    return jsonify({"success": True, "count": len(reviews), "data": reviews})

@app.route("/api/reviews/<int:review_id>", methods=["GET"])
def api_get_review(review_id):
    r = database.get_review_by_id(review_id)
    if not r:
        return jsonify({"success": False, "error": f"Review #{review_id} not found."}), 404
    return jsonify({"success": True, "data": r})

# -----------------------------------------------------------------------------
# 9. Integration Settings & Google Sheets APIs
# -----------------------------------------------------------------------------

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    db_settings = database.get_all_settings()
    ai_provider, ai_key, ai_model = AIService.get_effective_config()
    email_cfg = EmailService.get_effective_config()
    sheets_cfg = SheetsService.get_effective_config()
    scheduler_cfg = SchedulerService.get_status()

    # Mask secrets
    masked_key = f"{ai_key[:4]}...{ai_key[-4:]}" if ai_key and len(ai_key) > 8 else ("Configured" if ai_key else "Not set")
    masked_smtp_pass = "********" if email_cfg["smtp_pass"] else "Not set"

    return jsonify({
        "success": True,
        "ai": {
            "provider": ai_provider,
            "has_api_key": bool(ai_key),
            "masked_key": masked_key,
            "model": ai_model
        },
        "email": {
            "mode": email_cfg["mode"],
            "from_email": email_cfg["from_email"],
            "from_name": email_cfg["from_name"],
            "smtp_server": email_cfg["smtp_server"],
            "smtp_port": email_cfg["smtp_port"],
            "smtp_user": email_cfg["smtp_user"],
            "has_password": bool(email_cfg["smtp_pass"]),
            "smtp_tls": email_cfg["smtp_tls"]
        },
        "sheets": {
            "spreadsheet_id": sheets_cfg["spreadsheet_id"],
            "cred_exists": sheets_cfg["cred_exists"],
            "cred_path": sheets_cfg["cred_path"],
            "sheet_name": sheets_cfg["sheet_name"],
            "is_configured": sheets_cfg["is_configured"]
        },
        "scheduler": scheduler_cfg,
        "custom_settings": db_settings
    })

@app.route("/api/settings", methods=["POST"])
def api_update_settings():
    data = request.get_json() or {}
    for k, v in data.items():
        database.set_setting(k, v)
    return jsonify({"success": True, "message": "Settings updated successfully."})

@app.route("/api/sheets/sync", methods=["POST"])
def api_sheets_sync():
    result = SheetsService.sync_google_sheets()
    return jsonify(result)

@app.route("/api/sheets/import-csv", methods=["POST"])
def api_import_csv():
    if "file" in request.files:
        file = request.files["file"]
        content = file.read().decode("utf-8", errors="ignore")
    else:
        data = request.get_json() or {}
        content = data.get("csv_content", "")

    if not content.strip():
        return jsonify({"success": False, "error": "No CSV content provided."}), 400

    result = SheetsService.import_from_csv_text(content)
    return jsonify(result)

@app.route("/api/sheets/export-csv", methods=["GET"])
def api_export_csv():
    csv_str = SheetsService.export_to_csv_text()
    filename = f"recruitment_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_str,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# -----------------------------------------------------------------------------
# App Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=False)
