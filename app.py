import os
import time

from flask import Flask, flash, redirect, render_template, request, session, url_for, send_from_directory
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from mysql.connector import Error

import database
from gemini import evaluate_handwriting, extract_text
from image_processing import process_image

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "development-key")
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_score(scores):
    overall_score = (
        scores["letter_formation"] * 0.20
        + scores["word_spacing"] * 0.20
        + scores["alignment"] * 0.20
        + scores["slant_consistency"] * 0.15
        + scores["size_consistency"] * 0.10
        + scores["legibility"] * 0.15
    )
    return round(overall_score, 2)


def calculate_grade(score):
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def feedback_for_scores(scores):
    feedback = []
    labels = {
        "letter_formation": "letter formation",
        "word_spacing": "word spacing",
        "alignment": "alignment",
        "slant_consistency": "slant consistency",
        "size_consistency": "size consistency",
        "legibility": "legibility",
    }
    for metric, label in labels.items():
        if scores[metric] < 60:
            feedback.append(f"Practice {label} with slow, deliberate writing.")
    return feedback or ["Your handwriting is consistent across all six evaluated characteristics."]


@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        if not name or not email or not password:
            flash("Please fill in every field.")
            return render_template("register.html")
        try:
            database.create_user(name, email, generate_password_hash(password))
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))
        except Error:
            flash("That email is already registered or the database is unavailable.")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            user = database.find_user_by_email(request.form["email"].strip().lower())
        except Error:
            flash("The database is unavailable. Check your MySQL settings.")
            return render_template("login.html")
        if user and check_password_hash(user["password"], request.form["password"]):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role") == "teacher":
        evaluations = database.get_teacher_evaluations()
        return render_template("dashboard.html", teacher=True, evaluations=evaluations)
    evaluations = database.get_user_evaluations(session["user_id"])
    return render_template("dashboard.html", teacher=False, evaluations=evaluations)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        uploaded_file = request.files.get("image")
        if not uploaded_file or not uploaded_file.filename or not allowed_file(uploaded_file.filename):
            flash("Please upload a JPG, JPEG, or PNG image.")
            return render_template("upload.html")
        base_name = secure_filename(uploaded_file.filename)
        filename = f"{int(time.time())}_{base_name}"
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        uploaded_file.save(image_path)
        try:
            processed_path = process_image(image_path)
            extracted_text = extract_text(processed_path)
            scores = evaluate_handwriting(processed_path)
            overall_score = calculate_score(scores)
            grade = calculate_grade(overall_score)
            evaluation_id = database.save_evaluation(
                session["user_id"], filename, extracted_text, scores, overall_score, grade
            )
            return redirect(url_for("result", evaluation_id=evaluation_id))
        except (ValueError, RuntimeError, OSError, Error) as error:
            flash(f"Evaluation could not be completed: {error}")
    return render_template("upload.html")


@app.route("/result/<int:evaluation_id>")
def result(evaluation_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    owner_id = None if session.get("role") == "teacher" else session["user_id"]
    evaluation = database.get_evaluation(evaluation_id, owner_id)
    if not evaluation:
        flash("Evaluation not found.")
        return redirect(url_for("dashboard"))
    score_names = ("letter_formation", "word_spacing", "alignment", "slant_consistency", "size_consistency", "legibility")
    scores = {name: float(evaluation[name]) for name in score_names}

    processed_filename = f"{os.path.splitext(evaluation['image_path'])[0]}_processed.jpg"
    has_processed = os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], processed_filename))

    return render_template(
        "result.html",
        evaluation=evaluation,
        feedback=feedback_for_scores(scores),
        processed_filename=processed_filename if has_processed else None,
    )


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    if "user_id" not in session:
        return redirect(url_for("login"))
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("history.html", evaluations=database.get_user_evaluations(session["user_id"]))


if __name__ == "__main__":
    app.run(debug=True)
