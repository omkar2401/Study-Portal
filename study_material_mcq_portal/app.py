import os
import json
import re
import sqlite3
import secrets
from functools import wraps
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import fitz  # PyMuPDF

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-this-development-secret")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload limit
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
DATABASE = BASE_DIR / "portal.db"
ALLOWED_EXTENSIONS = {"pdf"}


def db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','student')),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT DEFAULT '',
            filename TEXT NOT NULL,
            extracted_text TEXT DEFAULT '',
            uploaded_by INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(uploaded_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL CHECK(correct_option IN ('A','B','C','D')),
            explanation TEXT DEFAULT '',
            published INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            answers_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id),
            FOREIGN KEY(material_id) REFERENCES materials(id)
        );
        """)
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        existing = conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO users(username,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                (admin_username, admin_email, generate_password_hash(admin_password), "admin", now())
            )


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def extract_pdf_text(path):
    doc = fitz.open(path)
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages).strip()


def generate_mcqs_with_ai(text, count=10):
    """Generate MCQs using OpenAI API. Returns list of validated question dictionaries."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AI generation is not configured. Add OPENAI_API_KEY to your .env file, or add questions manually.")

    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("The OpenAI package is missing. Run: pip install openai")

    # Keep prompt input bounded to control cost and avoid oversized requests.
    source_text = text[:24000]
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = f"""
Create {count} useful multiple-choice quiz questions based ONLY on the study text below.
Return valid JSON only, in this exact structure:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": {{"A":"option one","B":"option two","C":"option three","D":"option four"}},
      "correct_option": "A",
      "explanation": "Brief explanation grounded in the source"
    }}
  ]
}}
Rules:
- Exactly four distinct options A, B, C, D per question.
- Exactly one correct answer.
- correct_option must be A, B, C, or D.
- Avoid questions whose answer is not supported by the text.
- Do not include markdown fences.
Study text:
{source_text}
"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You create accurate educational MCQs and output strict JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError("The AI returned an unreadable response. Please try again.")
    questions = payload.get("questions", [])
    valid = []
    for item in questions:
        q = str(item.get("question", "")).strip()
        options = item.get("options", {})
        correct = str(item.get("correct_option", "")).upper().strip()
        explanation = str(item.get("explanation", "")).strip()
        if not q or correct not in {"A", "B", "C", "D"}:
            continue
        opts = {letter: str(options.get(letter, "")).strip() for letter in "ABCD"}
        if not all(opts.values()) or len(set(opts.values())) < 4:
            continue
        valid.append({
            "question": q, "options": opts, "correct_option": correct,
            "explanation": explanation
        })
    if not valid:
        raise RuntimeError("No valid MCQs were generated. Try a text-based PDF or add questions manually.")
    return valid[:count]


@app.route("/")
def index():
    if session.get("user_id"):
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("student_dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
        elif "@" not in email:
            flash("Enter a valid email address.", "danger")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            try:
                with db() as conn:
                    conn.execute(
                        "INSERT INTO users(username,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                        (username, email, generate_password_hash(password), "student", now())
                    )
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username or email is already registered.", "danger")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=? OR email=?", (username, username.lower())).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome, {user['username']}!", "success")
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "student_dashboard"))
        flash("Invalid username/email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required("admin")
def admin_dashboard():
    with db() as conn:
        materials = conn.execute("""
            SELECT m.*, COUNT(q.id) AS question_count
            FROM materials m LEFT JOIN questions q ON q.material_id=m.id
            GROUP BY m.id ORDER BY m.created_at DESC
        """).fetchall()
        student_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
        question_count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    return render_template("admin_dashboard.html", materials=materials, student_count=student_count, question_count=question_count)


@app.route("/admin/materials/upload", methods=["GET", "POST"])
@login_required("admin")
def upload_material():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("pdf")
        if not title or not subject:
            flash("Title and subject are required.", "danger")
            return redirect(url_for("upload_material"))
        if not file or not file.filename:
            flash("Choose a PDF file.", "danger")
            return redirect(url_for("upload_material"))
        if not allowed_file(file.filename):
            flash("Only PDF files are allowed.", "danger")
            return redirect(url_for("upload_material"))

        stored_name = f"{secrets.token_hex(12)}_{secure_filename(file.filename)}"
        path = UPLOAD_DIR / stored_name
        file.save(path)
        try:
            extracted = extract_pdf_text(path)
        except Exception:
            path.unlink(missing_ok=True)
            flash("The PDF could not be read. Please try another PDF.", "danger")
            return redirect(url_for("upload_material"))

        with db() as conn:
            cur = conn.execute(
                "INSERT INTO materials(title,subject,description,filename,extracted_text,uploaded_by,created_at) VALUES(?,?,?,?,?,?,?)",
                (title, subject, description, stored_name, extracted, session["user_id"], now())
            )
            material_id = cur.lastrowid
        if not extracted:
            flash("PDF uploaded, but no selectable text was found. Scanned PDFs need OCR before AI generation.", "warning")
        else:
            flash("PDF uploaded and text extracted successfully.", "success")
        return redirect(url_for("material_detail", material_id=material_id))
    return render_template("upload_material.html")


@app.route("/admin/material/<int:material_id>")
@login_required("admin")
def material_detail(material_id):
    with db() as conn:
        material = conn.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
        if not material:
            abort(404)
        questions = conn.execute("SELECT * FROM questions WHERE material_id=? ORDER BY id DESC", (material_id,)).fetchall()
    return render_template("material_detail.html", material=material, questions=questions)


@app.route("/admin/material/<int:material_id>/generate", methods=["POST"])
@login_required("admin")
def generate_questions(material_id):
    count = request.form.get("count", "10")
    try:
        count = max(1, min(20, int(count)))
    except ValueError:
        count = 10
    with db() as conn:
        material = conn.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    if not material:
        abort(404)
    if not material["extracted_text"].strip():
        flash("There is no extractable text in this PDF. Try a text-based PDF or add questions manually.", "danger")
        return redirect(url_for("material_detail", material_id=material_id))
    try:
        generated = generate_mcqs_with_ai(material["extracted_text"], count)
        with db() as conn:
            for item in generated:
                conn.execute("""
                    INSERT INTO questions(material_id,question,option_a,option_b,option_c,option_d,correct_option,explanation,published,created_at)
                    VALUES(?,?,?,?,?,?,?,?,0,?)
                """, (material_id, item["question"], item["options"]["A"], item["options"]["B"],
                      item["options"]["C"], item["options"]["D"], item["correct_option"], item["explanation"], now()))
        flash(f"Generated {len(generated)} draft questions. Review them and publish when ready.", "success")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("material_detail", material_id=material_id))


@app.route("/admin/material/<int:material_id>/question/new", methods=["GET", "POST"])
@login_required("admin")
def new_question(material_id):
    with db() as conn:
        material = conn.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    if not material:
        abort(404)
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        opts = [request.form.get(f"option_{letter.lower()}", "").strip() for letter in "ABCD"]
        correct = request.form.get("correct_option", "").upper()
        explanation = request.form.get("explanation", "").strip()
        if not question or not all(opts) or correct not in "ABCD":
            flash("Fill in the question, all four options, and correct answer.", "danger")
        else:
            with db() as conn:
                conn.execute("""
                    INSERT INTO questions(material_id,question,option_a,option_b,option_c,option_d,correct_option,explanation,published,created_at)
                    VALUES(?,?,?,?,?,?,?,?,0,?)
                """, (material_id, question, *opts, correct, explanation, now()))
            flash("Question saved as a draft.", "success")
            return redirect(url_for("material_detail", material_id=material_id))
    return render_template("question_form.html", material=material, question=None)


@app.route("/admin/question/<int:question_id>/edit", methods=["GET", "POST"])
@login_required("admin")
def edit_question(question_id):
    with db() as conn:
        question = conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
        if not question:
            abort(404)
        material = conn.execute("SELECT * FROM materials WHERE id=?", (question["material_id"],)).fetchone()
    if request.method == "POST":
        qtext = request.form.get("question", "").strip()
        opts = [request.form.get(f"option_{letter.lower()}", "").strip() for letter in "ABCD"]
        correct = request.form.get("correct_option", "").upper()
        explanation = request.form.get("explanation", "").strip()
        if not qtext or not all(opts) or correct not in "ABCD":
            flash("Fill in the question, all four options, and correct answer.", "danger")
        else:
            with db() as conn:
                conn.execute("""
                    UPDATE questions SET question=?,option_a=?,option_b=?,option_c=?,option_d=?,correct_option=?,explanation=?
                    WHERE id=?
                """, (qtext, *opts, correct, explanation, question_id))
            flash("Question updated.", "success")
            return redirect(url_for("material_detail", material_id=material["id"]))
    return render_template("question_form.html", material=material, question=question)


@app.route("/admin/question/<int:question_id>/publish", methods=["POST"])
@login_required("admin")
def publish_question(question_id):
    with db() as conn:
        q = conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
        if not q:
            abort(404)
        new_state = 0 if q["published"] else 1
        conn.execute("UPDATE questions SET published=? WHERE id=?", (new_state, question_id))
    flash("Question published for students." if new_state else "Question moved back to draft.", "success")
    return redirect(url_for("material_detail", material_id=q["material_id"]))


@app.route("/admin/question/<int:question_id>/delete", methods=["POST"])
@login_required("admin")
def delete_question(question_id):
    with db() as conn:
        q = conn.execute("SELECT material_id FROM questions WHERE id=?", (question_id,)).fetchone()
        if not q:
            abort(404)
        material_id = q["material_id"]
        conn.execute("DELETE FROM questions WHERE id=?", (question_id,))
    flash("Question deleted.", "info")
    return redirect(url_for("material_detail", material_id=material_id))


@app.route("/student")
@login_required("student")
def student_dashboard():
    with db() as conn:
        materials = conn.execute("""
            SELECT m.*, COUNT(q.id) AS question_count
            FROM materials m JOIN questions q ON q.material_id=m.id AND q.published=1
            GROUP BY m.id ORDER BY m.created_at DESC
        """).fetchall()
        recent = conn.execute("""
            SELECT a.*, m.title FROM attempts a JOIN materials m ON m.id=a.material_id
            WHERE a.student_id=? ORDER BY a.created_at DESC LIMIT 5
        """, (session["user_id"],)).fetchall()
    return render_template("student_dashboard.html", materials=materials, recent=recent)


@app.route("/student/material/<int:material_id>")
@login_required("student")
def student_material(material_id):
    with db() as conn:
        material = conn.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
        if not material:
            abort(404)
        questions = conn.execute("SELECT COUNT(*) FROM questions WHERE material_id=? AND published=1", (material_id,)).fetchone()[0]
    return render_template("student_material.html", material=material, question_count=questions)


@app.route("/student/material/<int:material_id>/pdf")
@login_required("student")
def view_pdf(material_id):
    with db() as conn:
        material = conn.execute("SELECT filename FROM materials WHERE id=?", (material_id,)).fetchone()
    if not material:
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], material["filename"], as_attachment=False)


@app.route("/student/material/<int:material_id>/quiz", methods=["GET", "POST"])
@login_required("student")
def take_quiz(material_id):
    with db() as conn:
        material = conn.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
        if not material:
            abort(404)
        questions = conn.execute("SELECT * FROM questions WHERE material_id=? AND published=1 ORDER BY id", (material_id,)).fetchall()
    if not questions:
        flash("There are no published questions for this material yet.", "warning")
        return redirect(url_for("student_material", material_id=material_id))
    if request.method == "POST":
        result = []
        score = 0
        answers = {}
        for q in questions:
            selected = request.form.get(f"q_{q['id']}", "").upper()
            correct = q["correct_option"]
            is_correct = selected == correct
            if is_correct:
                score += 1
            answers[str(q["id"])] = selected
            result.append({
                "id": q["id"], "question": q["question"], "selected": selected,
                "correct": correct, "is_correct": is_correct,
                "options": {"A": q["option_a"], "B": q["option_b"], "C": q["option_c"], "D": q["option_d"]},
                "explanation": q["explanation"]
            })
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO attempts(student_id,material_id,score,total,answers_json,created_at) VALUES(?,?,?,?,?,?)",
                (session["user_id"], material_id, score, len(questions), json.dumps(answers), now())
            )
            attempt_id = cur.lastrowid
        return render_template("quiz_result.html", material=material, result=result, score=score, total=len(questions), attempt_id=attempt_id)
    return render_template("quiz.html", material=material, questions=questions)


@app.route("/student/results")
@login_required("student")
def student_results():
    with db() as conn:
        attempts = conn.execute("""
            SELECT a.*, m.title, m.subject FROM attempts a
            JOIN materials m ON m.id=a.material_id
            WHERE a.student_id=? ORDER BY a.created_at DESC
        """, (session["user_id"],)).fetchall()
    return render_template("student_results.html", attempts=attempts)


@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You don't have permission to access this page."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The page or item could not be found."), 404


@app.errorhandler(413)
def too_large(_):
    flash("File is too large. Maximum upload size is 20 MB.", "danger")
    return redirect(request.referrer or url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
