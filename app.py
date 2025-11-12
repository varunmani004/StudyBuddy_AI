# ==============================================================
# 📘 STUDYBUDDY AI — PHASE 4 (Quiz + Learning Curve Tracker)
# Function: User system + Subject upload + AI Q&A chat + Quiz tracking
# ==============================================================

from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql, re, os, json, textwrap
from datetime import datetime, date
from werkzeug.utils import secure_filename
from text_extraction import extract_text
from modules.vector_store import add_text_file_to_vector_db, get_vector_store
from modules.chat_ai import get_ai_response_for_subject
from langchain_ollama import OllamaLLM
from datetime import date


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
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT", 3306))
    )

@app.route("/testdb")
def testdb():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT NOW()")
            result = cursor.fetchone()
        conn.close()
        return f"✅ Connected to MySQL! Server time: {result[0]}"
    except Exception as e:
        return f"❌ Database connection error: {e}"



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
            flash("✅ Registration successful! Please login.", "success")
            cursor.close()
            conn.close()
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


@app.route("/dashboard")
def dashboard():
    if "loggedin" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    username = session["username"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all subjects
    cursor.execute("SELECT * FROM subjects WHERE user_id=%s", (user_id,))
    subjects = cursor.fetchall()

    # Fetch quiz performance for each subject
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

    subject = get_subject(subject_id)
    file = request.files["file"]
    if not file or file.filename == "":
        flash("No file selected!", "warning")
        return redirect(url_for("subject_detail", subject_id=subject_id))

    filename = secure_filename(file.filename)
    subject_dir = os.path.join(app.config["UPLOAD_FOLDER"], str(subject_id))
    os.makedirs(subject_dir, exist_ok=True)
    save_path = os.path.join(subject_dir, filename)
    file.save(save_path)

    extracted_path = extract_text(save_path)
    os.makedirs(f"static/uploads/processed_texts/{subject_id}", exist_ok=True)
    processed_dest = os.path.join(f"static/uploads/processed_texts/{subject_id}", os.path.basename(extracted_path))
    os.replace(extracted_path, processed_dest)
    add_text_file_to_vector_db(processed_dest, subject_id)

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
# 🗑 DELETE FILE (Fix for subject_detail.html)
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
# 🧠 QUIZ GENERATION + NORMALIZATION
# ==============================================================
@app.route("/subjects/<int:subject_id>/generate_quiz_ai")
def generate_quiz_ai(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE subject_id=%s", (subject_id,))
    subject = cursor.fetchone()

    text_dir = f"static/uploads/processed_texts/{subject_id}"
    combined_text = ""
    if os.path.exists(text_dir):
        for fname in os.listdir(text_dir):
            if fname.endswith(".txt"):
                with open(os.path.join(text_dir, fname), "r", encoding="utf-8") as f:
                    combined_text += f.read() + "\n"

    if not combined_text.strip():
        flash("⚠️ No processed notes found. Upload notes first.", "warning")
        return redirect(url_for("subject_detail", subject_id=subject_id))

    try:
        llm = OllamaLLM(model="phi3:mini")
        prompt =  f"""
        You are a quiz generator.
        Create exactly 5 multiple-choice questions based on the text below.
        Output only a valid JSON array like this:
        [
          {{"question":"...","options":["A","B","C","D"],"answer":"A"}}
        ]

        Text:
        {combined_text[:4000]}
        """

        ai_output = str(llm.invoke(prompt))
        print("✅ Raw AI Output (preview):", ai_output[:400])

        start = ai_output.find("[")
        end = ai_output.rfind("]")
        json_str = ai_output[start:end+1]

        questions_list = []
        try:
            questions_list = json.loads(json_str)
        except Exception as e:
            print("⚠️ JSON parse failed:", e)
            # fallback: try to parse plain text into basic questions
            lines = [l.strip() for l in ai_output.splitlines() if l.strip()]
            temp = []
            q, opts = "", []
            for line in lines:
                if re.match(r'^\d+\.', line):  # e.g. "1. What is Java?"
                    if q and opts:
                        temp.append({"question": q, "options": opts, "answer": opts[0]})
                    q = re.sub(r'^\d+\.\s*', '', line)
                    opts = []
                elif re.match(r'^[A-D][\).\s-]', line):  # e.g. "A) Option"
                    opts.append(re.sub(r'^[A-D][\).\s-]+\s*', '', line))
            if q and opts:
                temp.append({"question": q, "options": opts, "answer": opts[0]})
            questions_list = temp


        normalized = []
        for q in questions_list:
            opts_raw = q.get("options", [])
            opts = []
            for o in opts_raw:
                if isinstance(o, list) and o:
                    opts.append(str(o[0]))
                elif isinstance(o, dict):
                    opts.append(o.get("text") or o.get("option") or str(o))
                else:
                    opts.append(str(o))
            opts = [o.strip() for o in opts if o.strip()][:4]
            ans = q.get("answer", "")
            if len(ans) == 1 and ans.upper() in ["A","B","C","D"]:
                idx = ord(ans.upper()) - ord("A")
                if idx < len(opts):
                    ans = opts[idx]
            normalized.append({
                "question": q.get("question", "Untitled Question").strip(),
                "options": opts or ["A","B","C","D"],
                "answer": ans or (opts[0] if opts else "A"),
            })

        cursor.execute("""
            INSERT INTO quizzes (subject_id, user_id, title, questions_json, difficulty)
            VALUES (%s,%s,%s,%s,%s)
        """, (subject_id, user_id, f"AI Quiz for {subject['subject_name']}",
              json.dumps(normalized, ensure_ascii=False), "Medium"))
        conn.commit()
        flash("✅ AI quiz generated successfully!", "success")
        print("💾 Quiz saved successfully!")
        return redirect(url_for("generate_quiz", subject_id=subject_id))

    except Exception as e:
        print("❌ ERROR in AI generation:", e)
        flash(f"❌ Quiz generation failed: {e}", "danger")
        return redirect(url_for("subject_detail", subject_id=subject_id))


# ==============================================================
# 📝 QUIZ PAGE + LEARNING CURVE
# ==============================================================

@app.route("/subjects/<int:subject_id>/quiz", methods=["GET", "POST"])
def generate_quiz(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # ✅ Load subject details
    cursor.execute("SELECT * FROM subjects WHERE subject_id=%s", (subject_id,))
    subject = cursor.fetchone()

    # 🧩 --- QUIZ SUBMISSION HANDLER ---
    if request.method == "POST":
        quiz_id = request.form.get("quiz_id")
        total = int(request.form.get("total", 0))
        user_id = session["user_id"]

        cursor.execute("SELECT * FROM quizzes WHERE id=%s", (quiz_id,))
        quiz = cursor.fetchone()

        if not quiz:
            flash("Quiz not found!", "danger")
            return redirect(url_for("subject_detail", subject_id=subject_id))

        # Parse quiz questions
        questions = json.loads(quiz["questions_json"])
        score = 0
        results = []

        # ✅ Calculate score
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
            # 🔹 1. Save quiz results
            cursor.execute("""
                INSERT INTO quiz_scores (quiz_id, user_id, subject_id, score, total, accuracy)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (quiz_id, user_id, subject_id, score, total, accuracy))
            conn.commit()

            # 🔹 2. Recalculate average accuracy
            cursor.execute("""
                SELECT AVG(accuracy) AS avg_acc
                FROM quiz_scores
                WHERE user_id=%s AND subject_id=%s
            """, (user_id, subject_id))
            avg_acc = cursor.fetchone()["avg_acc"] or 0

            # 🔹 3. Upsert learning curve data safely
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
            print("❌ Database error:", e)
            flash("Something went wrong while saving your quiz results.", "danger")
        finally:
            cursor.close()
            conn.close()

        # ✅ Render result page instead of redirect
        return render_template(
            "quiz_result.html",
            subject=subject,
            score=score,
            total=total,
            results=results
        )

    # 🧩 --- QUIZ DISPLAY (GET) ---
    cursor.execute(
        "SELECT * FROM quizzes WHERE subject_id=%s ORDER BY created_at DESC LIMIT 1",
        (subject_id,)
    )
    quiz = cursor.fetchone()
    cursor.close()
    conn.close()

    if not quiz:
        flash("No quiz available for this subject yet!", "warning")
        return redirect(url_for("subject_detail", subject_id=subject_id))

    try:
        questions = json.loads(quiz["questions_json"]) if quiz.get("questions_json") else []
        if not isinstance(questions, list):
            questions = [questions]
    except Exception as e:
        print("⚠️ Error decoding quiz JSON:", e)
        questions = []

    return render_template("quiz_page.html", subject=subject, quiz=quiz, questions=questions)


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
        SELECT AVG(avg_accuracy) AS avg_acc, COUNT(*) AS attempts
        FROM learning_curve WHERE user_id=%s AND subject_id=%s
    """, (user_id, subject_id))
    perf = cursor.fetchone() or {"avg_acc": 0, "attempts": 0}

    conn.close()

    # 🧠 Short personalized message
    if perf["avg_acc"] >= 80:
        advice = "Excellent grasp of concepts! Keep refining your skills with complex quizzes."
    elif perf["avg_acc"] >= 50:
        advice = "You're improving! Focus on understanding tricky topics through short revisions."
    else:
        advice = "Don't worry — focus on reattempting quizzes and reviewing explanations."

    return render_template("subject_learning_path.html",
                           subject=subject,
                           curve_data=curve_data,
                           avg_acc=perf["avg_acc"],
                           attempts=perf["attempts"],
                           advice=advice)




# ==============================================================
# Progress dashboard
# ==============================================================

@app.route("/progress_overview")
def progress_overview():
    if "loggedin" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all subjects
    cursor.execute("SELECT * FROM subjects WHERE user_id=%s", (user_id,))
    subjects = cursor.fetchall()

    # For each subject, calculate correct/wrong ratio
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
# Performance dashboard
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
    subjects_perf = cursor.fetchall()
    conn.close()
    return render_template("performance_dashboard.html", subjects=subjects_perf)



# ==============================================================
# 🚀 RUN SERVER
# ==============================================================
if __name__ == "__main__":
    app.run(debug=True)
