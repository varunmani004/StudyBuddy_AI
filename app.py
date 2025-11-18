# app.py (updated & fixed)
# ==============================================================
# 📘 STUDYBUDDY AI — PHASE 4 (Quiz + Learning Curve Tracker)
# ==============================================================

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql, re, os, json, textwrap
from datetime import datetime, date
from werkzeug.utils import secure_filename
from modules.text_extraction import extract_text
from modules.vector_store import add_text_file_to_vector_db, get_vector_store
from modules.chat_ai import get_ai_response_for_subject

# ============================================================== 
# 🔹 FLASK APP CONFIGURATION
# ============================================================== 
app = Flask(__name__)
app.secret_key = "studybuddy_secret_key_2025"
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

for folder in [
    "static/uploads",
    "static/uploads/pdfs",
    "static/uploads/docs",
    "static/uploads/processed_texts",
]:
    os.makedirs(folder, exist_ok=True)


# ============================================================== 
# ⚙️ DATABASE CONNECTION
# ============================================================== 
def get_db_connection():
    return pymysql.connect(
        host="trolley.proxy.rlwy.net",
        user="root",
        password="nsgEhetPqonqMUKkXuPSJfBOHoNweWoB",
        database="railway",
        port=10530,
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route("/testdb")
def test_db():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT NOW();")
            result = cur.fetchone()
        conn.close()
        return f"✅ Connected to MySQL! Time: {result}"
    except Exception as e:
        return f"❌ Error: {e}"


# ============================================================== 
# 🏠 HOME + AUTH SYSTEM
# ============================================================== 
@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s OR email=%s", (username, email))
        account = cursor.fetchone()

        if account:
            msg = "Account already exists!"
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            msg = "Invalid email address!"
        elif not re.match(r"[A-Za-z0-9]+", username):
            msg = "Username must contain only letters and numbers!"
        else:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s,%s,%s)",
                (username, email, password),
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash("✅ Registration successful! Please login.", "success")
            return redirect(url_for("login"))

        cursor.close()
        conn.close()

    return render_template("register.html", msg=msg)


@app.route("/login", methods=["GET", "POST"])
def login():
    msg = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        account = cursor.fetchone()
        cursor.close()
        conn.close()

        if account:
            session["loggedin"] = True
            session["user_id"] = account["id"]
            session["username"] = account["username"]
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            msg = "Incorrect username or password!"

    return render_template("login.html", msg=msg)


# ============================================================== 
# 📊 DASHBOARD
# ============================================================== 
@app.route("/dashboard")
def dashboard():
    if "loggedin" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    username = session["username"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM subjects WHERE user_id=%s", (user_id,))
    subjects = cursor.fetchall()

    subject_progress = []
    for subj in subjects:
        cursor.execute("""
            SELECT 
                COALESCE(SUM(score), 0) AS correct,
                COALESCE(SUM(total - score), 0) AS wrong,
                COUNT(*) AS attempts
            FROM quiz_scores WHERE user_id=%s AND subject_id=%s
        """, (user_id, subj["subject_id"]))
        stats = cursor.fetchone() or {}
        total = (stats["correct"] or 0) + (stats["wrong"] or 0)
        success = round((stats["correct"] / total * 100), 1) if total > 0 else 0

        subject_progress.append({
            "id": subj["subject_id"],
            "name": subj["subject_name"],
            "correct": stats["correct"] or 0,
            "wrong": stats["wrong"] or 0,
            "success": success
        })

    conn.close()

    return render_template(
        "dashboard.html",
        username=username,
        subjects_progress=subject_progress
    )


# ============================================================== 
# LOGOUT
# ============================================================== 
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out!", "info")
    return redirect(url_for("login"))


# ============================================================== 
# 📚 SUBJECT MANAGEMENT
# ============================================================== 
@app.route("/subjects")
def subjects():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE user_id=%s", (user_id,))
    subjects = cursor.fetchall()
    conn.close()
    return render_template("subjects.html", subjects=subjects)


@app.route("/subjects/add", methods=["POST"])
def add_subject():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    subject_name = request.form["subject_name"]
    description = request.form.get("description", "")
    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subjects (user_id, subject_name, description) VALUES (%s,%s,%s)",
        (user_id, subject_name, description),
    )
    conn.commit()
    conn.close()

    flash("Subject added successfully!", "success")
    return redirect(url_for("subjects"))


@app.route("/subjects/delete/<int:id>")
def delete_subject(id):
    if "loggedin" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subjects WHERE subject_id=%s", (id,))
    conn.commit()
    conn.close()
    flash("Subject deleted successfully!", "danger")
    return redirect(url_for("subjects"))


# ============================================================== 
# 📂 SUBJECT DETAIL PAGE
# ============================================================== 
def get_subject(subject_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE subject_id=%s", (subject_id,))
    subject = cursor.fetchone()
    conn.close()
    return subject


@app.route("/subjects/<int:subject_id>")
def subject_detail(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))
    subject = get_subject(subject_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM subject_files WHERE subject_id=%s ORDER BY uploaded_at DESC",
        (subject_id,),
    )
    files = cursor.fetchall()
    conn.close()
    return render_template("subject_detail.html", subject=subject, files=files, username=session["username"])


@app.route("/subjects/<int:subject_id>/upload", methods=["POST"])
def subject_upload(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    file = request.files.get("file")
    if not file or file.filename == "":
        flash("No file selected!", "warning")
        return redirect(url_for("subject_detail", subject_id=subject_id))

    filename = secure_filename(file.filename)
    subject_dir = os.path.join(app.config["UPLOAD_FOLDER"], str(subject_id))
    os.makedirs(subject_dir, exist_ok=True)
    save_path = os.path.join(subject_dir, filename)
    file.save(save_path)

    # IMPORTANT FIX: extract_text expects (file_path, subject_id)
    try:
        extracted_path = extract_text(save_path, subject_id)
        if not extracted_path:
            flash("⚠️ Could not extract text from this file (unsupported format).", "warning")
            # cleanup maybe
            return redirect(url_for("subject_detail", subject_id=subject_id))

        # Move/ensure processed path is inside correct folder (extract_text already writes there,
        # but keeping robust move in case extract_text wrote to a different temp path)
        processed_dir = os.path.join("static", "uploads", "processed_texts", str(subject_id))
        os.makedirs(processed_dir, exist_ok=True)
        processed_dest = os.path.join(processed_dir, os.path.basename(extracted_path))
        if os.path.abspath(extracted_path) != os.path.abspath(processed_dest):
            try:
                os.replace(extracted_path, processed_dest)
            except Exception:
                # if move fails, continue with original path
                processed_dest = extracted_path

        add_text_file_to_vector_db(processed_dest, subject_id)

    except TypeError as te:
        # If someone calls an old extract_text signature, show helpful error
        print("extract_text signature error:", te)
        flash("⚠️ Text extraction failed due to internal function signature mismatch.", "danger")
        return redirect(url_for("subject_detail", subject_id=subject_id))
    except Exception as e:
        print("Text extraction error:", e)
        flash(f"❌ Text extraction failed: {e}", "danger")
        return redirect(url_for("subject_detail", subject_id=subject_id))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subject_files (subject_id, user_id, filename, filepath, uploaded_at) VALUES (%s,%s,%s,%s,%s)",
        (subject_id, session["user_id"], filename, save_path, datetime.now()),
    )
    conn.commit()
    conn.close()
    flash("✅ File uploaded and indexed successfully!", "success")
    return redirect(url_for("subject_detail", subject_id=subject_id))


# ============================================================== 
# ✏️ EDIT SUBJECT
# ============================================================== 
@app.route("/edit_subject/<int:subject_id>", methods=["POST"])
def edit_subject(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    new_name = request.form.get("subject_name")
    new_desc = request.form.get("description")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subjects SET subject_name=%s, description=%s WHERE subject_id=%s",
        (new_name, new_desc, subject_id),
    )
    conn.commit()
    conn.close()

    flash("✏️ Subject updated successfully!", "info")
    return redirect(url_for("subjects"))


# ============================================================== 
# 🗑 DELETE FILE
# ============================================================== 
@app.route("/delete_file/<int:file_id>", methods=["POST"])
def delete_file(file_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT filepath, subject_id FROM subject_files WHERE file_id=%s", (file_id,))
    file = cursor.fetchone()

    if file:
        file_path = file["filepath"]
        subject_id = file["subject_id"]
        if os.path.exists(file_path):
            os.remove(file_path)
        cursor.execute("DELETE FROM subject_files WHERE file_id=%s", (file_id,))
        conn.commit()
        conn.close()
        flash("🗑 File removed successfully!", "info")
        return redirect(url_for("subject_detail", subject_id=subject_id))
    else:
        conn.close()
        flash("⚠️ File not found!", "warning")
        return redirect(url_for("subjects"))


# ============================================================== 
# 💬 SUBJECT CHAT
# ============================================================== 
@app.route("/subjects/<int:subject_id>/chat", methods=["GET", "POST"])
def subject_chat(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))
    subject = get_subject(subject_id)
    ai_reply, user_msg = None, None
    if request.method == "POST":
        user_msg = request.form.get("question")
        ai_reply = get_ai_response_for_subject(user_msg, subject_id) if user_msg else "Please enter a question."
    return render_template("chat_subject.html", subject=subject, ai_reply=ai_reply, user_msg=user_msg)


# ============================================================== 
# 🧠 QUIZ GENERATION (OpenRouter-only, robust)
# ============================================================== 
@app.route("/subjects/<int:subject_id>/generate_quiz_ai")
def generate_quiz_ai(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get subject
    cursor.execute("SELECT * FROM subjects WHERE subject_id=%s", (subject_id,))
    subject = cursor.fetchone()

    # Load processed notes
    text_dir = f"static/uploads/processed_texts/{subject_id}"
    combined_text = ""
    if os.path.exists(text_dir):
        for fname in os.listdir(text_dir):
            if fname.lower().endswith(".txt"):
                with open(os.path.join(text_dir, fname), "r", encoding="utf-8") as f:
                    combined_text += f.read() + "\n"

    if not combined_text.strip():
        flash("⚠️ No processed notes found. Upload notes first.", "warning")
        conn.close()
        return redirect(url_for("subject_detail", subject_id=subject_id))

    # Use OpenRouter JSON-only generator (defined in modules/groq_utils.py)
    from modules.groq_utils import openrouter_json_llm  # this returns a Python list (or empty list)

    prompt = f"""
Generate exactly 5 MCQ quiz questions from the following notes.

STRICT JSON OUTPUT ONLY in this exact format:
[
  {{
    "question": "....",
    "options": ["A", "B", "C", "D"],
    "answer": "A"
  }},
  ...
]

NOTES:
{combined_text[:7000]}
"""

    try:
        ai_result = openrouter_json_llm(prompt)  # expected: Python list (validated in groq_utils)

        # validate result
        if not isinstance(ai_result, list) or len(ai_result) == 0:
            raise ValueError("AI did not return a valid JSON array of questions.")

        questions_list = ai_result

        # Basic normalization/validation for each question (defensive)
        normalized = []
        for q in questions_list:
            q_text = q.get("question") if isinstance(q, dict) else None
            opts = q.get("options") if isinstance(q, dict) else None
            ans = q.get("answer") if isinstance(q, dict) else None

            if not q_text or not isinstance(opts, list) or len(opts) < 2:
                continue  # skip invalid entries

            # ensure exactly 4 options (pad if missing)
            opts = [str(o).strip() for o in opts][:4]
            while len(opts) < 4:
                opts.append("N/A")

            # if answer is A/B/C/D convert to actual option text
            if isinstance(ans, str) and len(ans.strip()) == 1 and ans.strip().upper() in ["A", "B", "C", "D"]:
                idx = ord(ans.strip().upper()) - ord("A")
                if idx < len(opts):
                    ans_text = opts[idx]
                else:
                    ans_text = opts[0]
            else:
                ans_text = str(ans).strip() if ans else opts[0]

            normalized.append({
                "question": str(q_text).strip(),
                "options": opts,
                "answer": ans_text
            })

        if not normalized:
            raise ValueError("AI returned no valid questions after normalization.")

        # Save into DB
        cursor.execute("""
            INSERT INTO quizzes (subject_id, user_id, title, questions_json, difficulty)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            subject_id,
            user_id,
            f"AI Quiz for {subject['subject_name']}",
            json.dumps(normalized, ensure_ascii=False),
            "Medium"
        ))
        conn.commit()
        conn.close()

        flash("✅ AI quiz generated successfully!", "success")
        return redirect(url_for("generate_quiz", subject_id=subject_id))

    except Exception as e:
        print("QUIZ ERROR:", e)
        try:
            conn.close()
        except Exception:
            pass
        flash(f"❌ Quiz generation failed: {e}", "danger")
        return redirect(url_for("subject_detail", subject_id=subject_id))


# ============================================================== 
# 📝 QUIZ PAGE + RESULT + LEARNING CURVE
# ============================================================== 
@app.route("/subjects/<int:subject_id>/quiz", methods=["GET", "POST"])
def generate_quiz(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT * FROM subjects WHERE subject_id=%s", (subject_id,))
    subject = cursor.fetchone()

    # POST: user submits quiz
    if request.method == "POST":
        quiz_id = request.form.get("quiz_id")
        total = int(request.form.get("total", 0))
        user_id = session["user_id"]

        cursor.execute("SELECT * FROM quizzes WHERE id=%s", (quiz_id,))
        quiz = cursor.fetchone()

        if not quiz:
            flash("Quiz not found!", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for("subject_detail", subject_id=subject_id))

        questions = json.loads(quiz["questions_json"])
        score = 0
        results = []

        for i, q in enumerate(questions, start=1):
            selected = request.form.get(f"q{i}")
            correct = q.get("answer", "").strip().lower()
            is_correct = selected and selected.strip().lower() == correct
            if is_correct:
                score += 1
            results.append({
                "question": q.get("question"),
                "selected": selected,
                "correct": correct,
                "is_correct": is_correct
            })

        accuracy = round(score / total, 2) if total else 0

        try:
            cursor.execute("""
                INSERT INTO quiz_scores (quiz_id, user_id, subject_id, score, total, accuracy)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (quiz_id, user_id, subject_id, score, total, accuracy))
            conn.commit()

            cursor.execute("""
                SELECT AVG(accuracy) AS avg_acc
                FROM quiz_scores
                WHERE user_id=%s AND subject_id=%s
            """, (user_id, subject_id))
            avg_acc = cursor.fetchone()["avg_acc"] or 0

            cursor.execute("""
                INSERT INTO learning_curve (user_id, subject_id, date, avg_accuracy, total_study_time, predicted_mastery)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    avg_accuracy = VALUES(avg_accuracy),
                    predicted_mastery = VALUES(predicted_mastery)
            """, (user_id, subject_id, date.today(), avg_acc, 0, avg_acc * 100))
            conn.commit()

        except pymysql.MySQLError as e:
            conn.rollback()
            print("DB save error:", e)
            flash("❌ Something went wrong while saving your quiz results.", "danger")

        finally:
            cursor.close()
            conn.close()

        return render_template(
            "quiz_result.html",
            subject=subject,
            score=score,
            total=total,
            results=results
        )

    # GET: show latest quiz
    cursor.execute(
        "SELECT * FROM quizzes WHERE subject_id=%s ORDER BY created_at DESC LIMIT 1",
        (subject_id,)
    )
    quiz = cursor.fetchone()
    cursor.close()
    conn.close()

    if not quiz:
        flash("No quiz available yet!", "warning")
        return redirect(url_for("subject_detail", subject_id=subject_id))

    try:
        questions = json.loads(quiz["questions_json"])
    except Exception as e:
        print("⚠️ Error decoding quiz JSON:", e)
        questions = []

    return render_template("quiz_page.html", subject=subject, quiz=quiz, questions=questions)


# ============================================================== 
# 📈 SUBJECT PROGRESS PAGE
# ============================================================== 
@app.route("/subjects/<int:subject_id>/progress")
def subject_progress(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM subjects WHERE subject_id=%s", (subject_id,))
    subject = cursor.fetchone()

    cursor.execute("""
        SELECT date, avg_accuracy, predicted_mastery 
        FROM learning_curve
        WHERE user_id=%s AND subject_id=%s ORDER BY date
    """, (user_id, subject_id))
    curve_data = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(AVG(avg_accuracy), 0) AS avg_acc, COUNT(*) AS attempts
        FROM learning_curve 
        WHERE user_id=%s AND subject_id=%s
    """, (user_id, subject_id))
    perf = cursor.fetchone()

    avg_acc = perf["avg_acc"] or 0
    attempts = perf["attempts"] or 0

    conn.close()

    if avg_acc >= 80:
        advice = "Excellent grasp of concepts! Keep refining."
    elif avg_acc >= 50:
        advice = "You're improving! Focus on tricky topics."
    else:
        advice = "Don't worry — revise and reattempt quizzes."

    return render_template(
        "subject_learning_path.html",
        subject=subject,
        curve_data=curve_data,
        avg_acc=avg_acc,
        attempts=attempts,
        advice=advice
    )


# ============================================================== 
# 📊 PROGRESS OVERVIEW PAGE
# ============================================================== 
@app.route("/progress_overview")
def progress_overview():
    if "loggedin" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM subjects WHERE user_id=%s", (user_id,))
    subjects = cursor.fetchall()

    subject_stats = []
    for subj in subjects:
        cursor.execute("""
            SELECT SUM(score) AS total_correct, SUM(total - score) AS total_wrong, COUNT(*) AS quizzes
            FROM quiz_scores WHERE user_id=%s AND subject_id=%s
        """, (user_id, subj["subject_id"]))
        stats = cursor.fetchone() or {}
        
        total_correct = stats.get("total_correct", 0) or 0
        total_wrong = stats.get("total_wrong", 0) or 0
        total_attempts = total_correct + total_wrong
        success_rate = (total_correct / total_attempts * 100) if total_attempts > 0 else 0

        subject_stats.append({
            "id": subj["subject_id"],
            "name": subj["subject_name"],
            "correct": total_correct,
            "wrong": total_wrong,
            "success_rate": round(success_rate, 1)
        })

    conn.close()
    return render_template("progress_overview.html", subjects=subject_stats)


# ============================================================== 
# 📉 PERFORMANCE DASHBOARD
# ============================================================== 
@app.route("/performance")
def performance_dashboard():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.subject_id, s.subject_name, AVG(qs.accuracy) AS avg_accuracy
        FROM subjects s
        LEFT JOIN quiz_scores qs ON s.subject_id = qs.subject_id AND qs.user_id=%s
        WHERE s.user_id=%s
        GROUP BY s.subject_id
    """, (user_id, user_id))

    raw_data = cursor.fetchall()
    conn.close()

    subjects = []
    for row in raw_data:
        subjects.append({
            "id": row["subject_id"],
            "subject_name": row["subject_name"],
            "avg_accuracy": row["avg_accuracy"] or 0
        })

    return render_template("performance_dashboard.html", subjects=subjects)


# ============================================================== 
# 🚀 RUN SERVER
# ============================================================== 
if __name__ == "__main__":
    app.run(debug=True)
