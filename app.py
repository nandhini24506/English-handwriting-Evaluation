"""EHE 2.0 — AI-Assisted English Handwriting Evaluation and Improvement System

Main Flask Application Architecture
"""

import os
import io
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    send_file,
    send_from_directory,
    abort,
)
from dotenv import load_dotenv
from mysql.connector import Error

# Load environment configuration
load_dotenv()

# Import specialized modular subsystems
import database
import auth
from auth import login_required, student_required, validate_csrf_token, admin_required
from teacher import teacher_required, verify_evaluation_access
import image_upload
import image_processing
import handwriting_evaluation
import scoring
import feedback
import practice
import progress
import reports
import ocr

# Initialize Flask application
app = Flask(__name__)

# Validate and configure SECRET_KEY
env_secret = os.getenv("SECRET_KEY", "").strip()
is_production = os.getenv("FLASK_ENV", "").lower() == "production" or os.getenv("ENV", "").lower() == "production"

if is_production and (not env_secret or env_secret.startswith("replace_with")):
    raise RuntimeError(
        "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY environment variable is required "
        "and must not use a placeholder value in production environments."
    )

app.config["SECRET_KEY"] = env_secret or "ehe-2.0-stable-local-session-secret-key-2026"
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB limit

# Secure Session Cookie configuration
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Safe database initialization on startup
try:
    database.initialize_database()
except Exception as _db_init_err:
    app.logger.warning(f"Database initialization at startup deferred: {_db_init_err}")


# =========================================================================
# Security & CSRF Middleware
# =========================================================================

@app.context_processor
def inject_csrf_token():
    """Injects csrf_token helper into all Jinja templates."""
    return {
        "csrf_token": auth.generate_csrf_token,
    }


@app.before_request
def handle_csrf():
    """Ensures session has a CSRF token on GET, and validates on state-changing requests."""
    # Ensure CSRF token exists in session for all requests
    if "csrf_token" not in session:
        auth.generate_csrf_token()

    # Validate state-changing methods
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        if not auth.validate_csrf_token(token):
            # Refresh token so a reloaded form has a fresh valid token
            auth.generate_csrf_token()
            flash("Your session security token was invalid or has expired. A fresh security token has been generated. Please try again.", "error")
            referrer = request.referrer
            if referrer and request.host in referrer:
                return redirect(referrer)
            return render_template(
                "csrf_error.html",
                message="Your session security token was invalid or has expired. Please reload the page to obtain a fresh token and try again.",
                return_url=request.referrer or url_for("login"),
            ), 400


# =========================================================================
# Authentication & Navigation Routes
# =========================================================================

@app.route("/")
def home():
    """Landing route: redirects authenticated users to dashboard, others to login."""
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Public user registration. Always assigns student role."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        # Inspect for role escalation attempts
        submitted_role = request.form.get("role", "").strip().lower()

        is_valid, error_msg = auth.validate_registration_form(name, email, password, role=submitted_role)
        if not is_valid:
            flash(error_msg, "error")
            return render_template("register.html"), 400

        try:
            password_hash = auth.hash_password(password)
            # Public registration ALWAYS assigns role="student" server-side
            database.create_user(name, email, password_hash, role="student")
            flash("Account successfully created. Please sign in with your credentials.", "success")
            return redirect(url_for("login"))
        except Error as err:
            flash("Registration failed: That email address is already registered or the database is unavailable.", "error")
        except Exception as err:
            flash("An unexpected error occurred during registration. Please try again.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """User authentication and session initialization."""
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        try:
            user = database.find_user_by_email(email)
            if user and auth.verify_password(password, user["password"]):
                auth.login_user(user)
                flash(f"Welcome back, {user['name']}!", "success")
                if user.get("role") == "admin":
                    return redirect(url_for("admin_dashboard"))
                return redirect(url_for("dashboard"))
            flash("Invalid email address or password. Please verify your credentials.", "error")
        except Error:
            flash("Database service is currently unreachable. Please check your MySQL settings.", "error")
        except Exception:
            flash("Authentication error. Please try again.", "error")

    return render_template("login.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Administrator authentication route."""
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        # Non-admin user visiting admin login should not be silently upgraded
        flash("You are currently signed in as a non-administrator account. Please sign in with administrator credentials.", "warning")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        try:
            user = database.find_user_by_email(email)
            if not user or not auth.verify_password(password, user["password"]):
                flash("Invalid administrator email address or password.", "error")
                return render_template("admin_login.html"), 401

            if user.get("role") != "admin":
                flash("Access denied. This account does not possess administrator privileges.", "error")
                return render_template("admin_login.html"), 403

            # Clear session to prevent session fixation and initialize admin session
            session.clear()
            auth.login_user(user)
            flash(f"Welcome to the EHE 2.0 Admin Console, {user['name']}!", "success")
            return redirect(url_for("admin_dashboard"))
        except Error:
            flash("Database service is currently unreachable.", "error")
        except Exception:
            flash("Administrator authentication error. Please try again.", "error")

    return render_template("admin_login.html")


@app.route("/admin")
@admin_required
def admin_dashboard():
    """Protected administrator dashboard."""
    stats = database.get_admin_dashboard_stats()
    users = database.list_all_users_for_admin(limit=100)
    recent_evaluations = database.list_recent_evaluations_for_admin(limit=10)
    ai_provider = "Gemini Vision (Active)" if os.getenv("GEMINI_API_KEY") else "NVIDIA Multimodal"

    system_health = {
        "ai_provider": ai_provider,
        "database_status": "Connected",
    }

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        users=users,
        recent_evaluations=recent_evaluations,
        system_health=system_health,
    )


@app.route("/admin/logout", methods=["GET", "POST"])
def admin_logout():
    """Protected administrator logout."""
    if request.method == "POST":
        auth.logout_user()
        flash("You have been signed out of the administrator console.", "info")
        return redirect(url_for("admin_login"))
    # Direct GET access redirects safely
    return redirect(url_for("admin_login"))


@app.route("/logout")
def logout():
    """Terminates session and redirects to sign-in."""
    auth.logout_user()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("login"))


# =========================================================================
# Dashboard
# =========================================================================

@app.route("/dashboard")
@login_required
def dashboard():
    """Role-aware dashboard for students and teachers."""
    user_id = session["user_id"]
    role = session.get("role", "student")

    try:
        if role == "teacher":
            evaluations = database.get_teacher_evaluations()
            students = database.list_students()
            return render_template("dashboard.html", teacher=True, evaluations=evaluations, students=students)
        else:
            evaluations = database.get_user_evaluations(user_id)
            weakest_metric = None
            if evaluations:
                latest = evaluations[0]
                latest_scores = {
                    "letter_formation": float(latest["letter_formation"]),
                    "word_spacing": float(latest["word_spacing"]),
                    "alignment": float(latest["alignment"]),
                    "slant_consistency": float(latest["slant_consistency"]),
                    "size_consistency": float(latest["size_consistency"]),
                    "legibility": float(latest["legibility"]),
                }
                weakest_metric = feedback.identify_weakest_metric(latest_scores)

            return render_template("dashboard.html", teacher=False, evaluations=evaluations, weakest_metric=weakest_metric)
    except Error:
        flash("Could not retrieve dashboard records from database.", "error")
        return render_template("dashboard.html", teacher=(role == "teacher"), evaluations=[])


# =========================================================================
# Handwriting Upload & Evaluation
# =========================================================================

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Upload workspace and multimodal evaluation initiation."""
    user_id = session["user_id"]
    active_assignments = []
    try:
        active_assignments = database.get_student_assignments(user_id)
    except Exception:
        pass

    if request.method == "POST":
        uploaded_file = request.files.get("image")
        assignment_id_raw = request.form.get("assignment_id")
        assignment_id = int(assignment_id_raw) if assignment_id_raw and assignment_id_raw.isdigit() else None

        try:
            # 1. Strict file content validation and safe saving
            saved_filename, full_image_path, image_hash = image_upload.save_uploaded_file(
                uploaded_file, app.config["UPLOAD_FOLDER"]
            )

            # 2. OpenCV Image Preprocessing (EXIF, resize, CLAHE)
            processed_path = image_processing.process_image(full_image_path)

            # 3. Multimodal AI Evaluation with SHA-256 byte caching & CV feature extraction
            eval_bundle = handwriting_evaluation.evaluate_handwriting_bundle(
                image_path=processed_path,
                image_hash=image_hash,
                db_lookup_fn=database.get_cached_evaluation,
                db_store_fn=database.save_cached_evaluation,
            )

            # 4. Generate Rule-Based Feedback
            rule_feedback = feedback.generate_feedback(
                scores=eval_bundle["scores"],
                cv_features=eval_bundle.get("cv_features"),
            )

            # 5. Save Evaluation to MySQL database
            eval_id = database.save_evaluation(
                user_id=user_id,
                image_path=saved_filename,
                extracted_text=eval_bundle["transcription"],
                scores=eval_bundle["scores"],
                overall_score=eval_bundle["overall_score"],
                grade=eval_bundle["grade"],
                image_hash=image_hash,
                cv_features=eval_bundle.get("cv_features"),
                ai_feedback=rule_feedback,
                assignment_id=assignment_id,
            )

            flash("Handwriting sample analyzed successfully!", "success")
            return redirect(url_for("result", evaluation_id=eval_id))

        except ValueError as err:
            flash(f"Validation Notice: {err}", "error")
        except RuntimeError as err:
            flash(f"Evaluation Service Notice: {err}", "error")
        except Error as err:
            flash("Database error: Could not record evaluation results.", "error")
        except Exception as err:
            flash(f"An unexpected error occurred during evaluation: {err}", "error")

    return render_template("upload.html", active_assignments=active_assignments)


# =========================================================================
# Evaluation Result & Showcase
# =========================================================================

@app.route("/result/<int:evaluation_id>")
@login_required
def result(evaluation_id):
    """Detailed showcase report for a specific evaluation."""
    user_id = session["user_id"]
    role = session.get("role", "student")

    # Teachers can view any evaluation; students can only view their own
    owner_filter = None if role == "teacher" else user_id
    evaluation = database.get_evaluation(evaluation_id, owner_filter)

    if not evaluation:
        flash("Evaluation report not found or access denied.", "error")
        return redirect(url_for("dashboard"))

    # Extract score metrics
    score_names = [
        "letter_formation",
        "word_spacing",
        "alignment",
        "slant_consistency",
        "size_consistency",
        "legibility",
    ]
    scores = {name: float(evaluation[name]) for name in score_names}
    score_breakdown = scoring.get_score_breakdown(scores)

    # Check for processed image
    base_stem = os.path.splitext(evaluation["image_path"])[0]
    processed_filename = f"{base_stem}_processed.jpg"
    has_processed = os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], processed_filename))

    # Retrieve CV features & Feedback
    cv_features = evaluation.get("cv_features")
    rule_feedback = evaluation.get("ai_feedback") or feedback.generate_feedback(scores, cv_features)

    # Retrieve OCR Corrections
    ocr_corrections = database.get_ocr_corrections(evaluation_id)

    # Reconstruct metric details
    metric_details = {}
    for name in score_names:
        metric_details[name] = {
            "score": scores[name],
            "explanation": f"Evaluated metric for {name.replace('_', ' ')}.",
            "evidence": "",
        }

    return render_template(
        "result.html",
        evaluation=evaluation,
        score_breakdown=score_breakdown,
        metric_details=metric_details,
        cv_features=cv_features,
        feedback=rule_feedback,
        ocr_corrections=ocr_corrections,
        processed_filename=processed_filename if has_processed else None,
    )


@app.route("/result/<int:evaluation_id>/correct-ocr", methods=["POST"])
@login_required
def correct_ocr(evaluation_id):
    """Saves user-submitted transcription correction."""
    user_id = session["user_id"]
    role = session.get("role", "student")
    owner_filter = None if role == "teacher" else user_id
    evaluation = database.get_evaluation(evaluation_id, owner_filter)

    if not evaluation:
        flash("Evaluation not found.", "error")
        return redirect(url_for("dashboard"))

    corrected_text = request.form.get("corrected_text", "").strip()
    try:
        ocr.record_ocr_correction(
            evaluation_id=evaluation_id,
            user_id=user_id,
            original_text=evaluation["extracted_text"],
            corrected_text=corrected_text,
            save_fn=database.save_ocr_correction,
        )
        flash("Transcription correction recorded successfully.", "success")
    except ValueError as err:
        flash(str(err), "warning")
    except Exception:
        flash("Could not record correction due to a server error.", "error")

    return redirect(url_for("result", evaluation_id=evaluation_id))


@app.route("/result/<int:evaluation_id>/download-pdf")
@login_required
def download_pdf(evaluation_id):
    """Generates and serves downloadable PDF evaluation report via ReportLab."""
    user_id = session["user_id"]
    role = session.get("role", "student")
    owner_filter = None if role == "teacher" else user_id
    evaluation = database.get_evaluation(evaluation_id, owner_filter)

    if not evaluation:
        flash("Evaluation not found for PDF export.", "error")
        return redirect(url_for("dashboard"))

    try:
        # Full image path if present
        image_full_path = os.path.join(app.config["UPLOAD_FOLDER"], evaluation["image_path"])
        student_name = evaluation.get("name", "Student")
        feedbacks = evaluation.get("ai_feedback") or []

        pdf_bytes = reports.generate_pdf_report(
            evaluation=evaluation,
            student_name=student_name,
            feedback_items=feedbacks,
            image_full_path=image_full_path if os.path.exists(image_full_path) else None,
        )

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"EHE_Report_Assessment_{evaluation_id}.pdf",
        )
    except Exception as err:
        flash(f"Failed to generate PDF report: {err}", "error")
        return redirect(url_for("result", evaluation_id=evaluation_id))


# =========================================================================
# Progress Analytics & Trends
# =========================================================================

@app.route("/progress")
@login_required
@student_required
def progress_view():
    """Historical handwriting performance analytics and trajectory visualization."""
    user_id = session["user_id"]
    evaluations = database.get_user_evaluations(user_id)
    analytics = progress.calculate_progress_analytics(evaluations)
    return render_template("progress.html", analytics=analytics)


# =========================================================================
# Personalised Practice Centre
# =========================================================================

@app.route("/practice")
@login_required
@student_required
def practice_view():
    """Practice centre offering deterministic exercises focused on evaluated weaknesses."""
    user_id = session["user_id"]
    evaluations = database.get_user_evaluations(user_id)

    weakest_metric = None
    latest_eval_id = None

    if evaluations:
        latest = evaluations[0]
        latest_eval_id = latest["id"]
        latest_scores = {
            "letter_formation": float(latest["letter_formation"]),
            "word_spacing": float(latest["word_spacing"]),
            "alignment": float(latest["alignment"]),
            "slant_consistency": float(latest["slant_consistency"]),
            "size_consistency": float(latest["size_consistency"]),
            "legibility": float(latest["legibility"]),
        }
        weakest_metric = feedback.identify_weakest_metric(latest_scores)

    target_metric_key = weakest_metric["metric"] if weakest_metric else "letter_formation"
    exercises = practice.get_recommended_exercises(target_metric_key)
    practice_history = database.get_user_practice_activities(user_id)

    return render_template(
        "practice.html",
        weakest_metric=weakest_metric,
        latest_eval_id=latest_eval_id,
        exercises=exercises,
        practice_history=practice_history,
    )


@app.route("/practice/complete", methods=["POST"])
@login_required
@student_required
def complete_practice():
    """Logs completion of a targeted practice activity."""
    user_id = session["user_id"]
    title = request.form.get("exercise_title", "Handwriting Drill").strip()
    text = request.form.get("exercise_text", "").strip()
    metric = request.form.get("metric_targeted", "letter_formation").strip()
    notes = request.form.get("notes", "").strip()

    try:
        activity_id = database.save_practice_activity(
            user_id=user_id,
            metric_targeted=metric,
            exercise_title=title,
            exercise_text=text,
        )
        database.mark_practice_completed(activity_id, user_id, notes)
        flash(f"Practice drill '{title}' logged as completed!", "success")
    except Exception:
        flash("Could not log practice activity due to a database error.", "error")

    return redirect(url_for("practice_view"))


# =========================================================================
# Teacher Management & Classes
# =========================================================================

@app.route("/teacher/classes")
@login_required
@teacher_required
def teacher_classes_view():
    """Teacher portal for managing classes, rosters, and assignments."""
    teacher_id = session["user_id"]
    classes = database.get_teacher_classes(teacher_id)
    assignments = database.get_assignments_for_teacher(teacher_id)
    return render_template("teacher_classes.html", classes=classes, assignments=assignments)


@app.route("/teacher/classes/create", methods=["POST"])
@login_required
@teacher_required
def create_class_route():
    """Endpoint for teachers to create a new class cohort."""
    teacher_id = session["user_id"]
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    description = request.form.get("description", "").strip()

    if not name or not code:
        flash("Class name and class code are required.", "error")
        return redirect(url_for("teacher_classes_view"))

    try:
        database.create_class(teacher_id, name, code, description)
        flash(f"Class '{name}' (Code: {code}) created successfully!", "success")
    except Error:
        flash("A class with that unique code already exists or database error occurred.", "error")

    return redirect(url_for("teacher_classes_view"))


@app.route("/teacher/assignments/create", methods=["POST"])
@login_required
@teacher_required
def create_assignment_route():
    """Endpoint for teachers to publish an assignment."""
    teacher_id = session["user_id"]
    class_id = int(request.form.get("class_id", 0))
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date = request.form.get("due_date", "").strip() or None

    if not title or not class_id:
        flash("Assignment title and target class are required.", "error")
        return redirect(url_for("teacher_classes_view"))

    try:
        database.create_assignment(class_id, teacher_id, title, description, due_date)
        flash(f"Assignment '{title}' published for class members!", "success")
    except Exception:
        flash("Failed to publish assignment.", "error")

    return redirect(url_for("teacher_classes_view"))


# =========================================================================
# Evaluation History & Upload Serving
# =========================================================================

@app.route("/history")
@login_required
def history():
    """Archived evaluation submissions."""
    user_id = session["user_id"]
    role = session.get("role", "student")

    if role == "teacher":
        evaluations = database.get_teacher_evaluations()
    else:
        evaluations = database.get_user_evaluations(user_id)

    return render_template("history.html", evaluations=evaluations)


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    """Secure authenticated file serving from upload folder."""
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# =========================================================================
# HTTP Error Handlers
# =========================================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template("base.html", content="""
        <div class="card" style="text-align: center; padding: 50px 20px;">
          <h1 style="font-size: 28px; font-weight: 700; margin-bottom: 8px;">404 — Page Not Found</h1>
          <p style="color: var(--text-muted); margin-bottom: 20px;">The requested page or resource could not be found.</p>
          <a href="/" class="btn btn-primary">Return to Dashboard</a>
        </div>
    """), 404


@app.errorhandler(403)
def forbidden_error(error):
    return render_template("base.html", content="""
        <div class="card" style="text-align: center; padding: 50px 20px;">
          <h1 style="font-size: 28px; font-weight: 700; margin-bottom: 8px;">403 — Access Denied</h1>
          <p style="color: var(--text-muted); margin-bottom: 20px;">You do not possess the required permissions to access this evaluation record.</p>
          <a href="/" class="btn btn-primary">Return to Dashboard</a>
        </div>
    """), 403


@app.errorhandler(500)
def internal_error(error):
    return render_template("base.html", content="""
        <div class="card" style="text-align: center; padding: 50px 20px;">
          <h1 style="font-size: 28px; font-weight: 700; margin-bottom: 8px;">500 — Internal Server Error</h1>
          <p style="color: var(--text-muted); margin-bottom: 20px;">An internal processing error occurred. Please contact your administrator.</p>
          <a href="/" class="btn btn-primary">Return to Dashboard</a>
        </div>
    """), 500


if __name__ == "__main__":
    app.run(debug=True)
