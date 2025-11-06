# ==============================================================
# 📘 STUDYBUDDY AI — PHASE 3 (FINAL REFINED)
# Function: User system + Subject upload + AI Q&A chat
# ==============================================================

from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
import re
import os
from werkzeug.utils import secure_filename
from datetime import datetime

# Internal modules
from text_extraction import extract_text
from modules.vector_store import add_text_file_to_vector_db
from modules.chat_ai import get_ai_response_for_subject


# ==============================================================
# 🔹 FLASK APP CONFIGURATION
# ==============================================================

app = Flask(__name__)
app.secret_key = "studybuddy_secret_key_2025"
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB limit

# Create directories if not exist
for folder in [
    "static/uploads",
    "static/uploads/pdfs",
    "static/uploads/docs",
    "static/uploads/processed_texts",
]:
    os.makedirs(folder, exist_ok=True)


# ==============================================================
# ⚙️ DATABASE CONNECTION SETUP
# ==============================================================

def get_db_connection():
    """Return MySQL connection"""
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="studybuddy_db",
        cursorclass=pymysql.cursors.DictCursor,
    )


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
    if "loggedin" in session:
        return render_template("dashboard.html", username=session["username"])
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out!", "info")
    return redirect(url_for("login"))


# ==============================================================
# 📚 SUBJECT MANAGEMENT (Add / Edit / Delete)
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


@app.route("/edit_subject/<int:subject_id>", methods=["POST"])
def edit_subject(subject_id):
    new_name = request.form.get("subject_name")
    new_desc = request.form.get("description")

    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE subjects SET subject_name=%s, description=%s WHERE subject_id=%s",
            (new_name, new_desc, subject_id),
        )
    connection.commit()
    connection.close()

    flash("Subject updated successfully!", "info")
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
# 📂 SUBJECT DETAIL PAGE (Upload + Remove Files)
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

    return render_template("subject_detail.html", subject=subject, files=files)


@app.route("/subjects/<int:subject_id>/upload", methods=["POST"])
def subject_upload(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    subject = get_subject(subject_id)
    if not subject:
        flash("Subject not found!", "danger")
        return redirect(url_for("subjects"))

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


@app.route("/delete_file/<int:file_id>", methods=["POST"])
def delete_file(file_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT filepath, subject_id FROM subject_files WHERE file_id=%s", (file_id,))
        file = cursor.fetchone()

        if file:
            file_path = file["filepath"]
            subject_id = file["subject_id"]

            if os.path.exists(file_path):
                os.remove(file_path)

            cursor.execute("DELETE FROM subject_files WHERE file_id=%s", (file_id,))
            connection.commit()
            connection.close()

            flash("🗑 File removed successfully!", "info")
            return redirect(url_for("subject_detail", subject_id=subject_id))

    connection.close()
    flash("⚠️ File not found!", "warning")
    return redirect(url_for("subjects"))


# ==============================================================
# 💬 SUBJECT CHAT (Q&A per Subject)
# ==============================================================

@app.route("/subjects/<int:subject_id>/chat", methods=["GET", "POST"])
def subject_chat(subject_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    subject = get_subject(subject_id)
    ai_reply = None
    user_msg = None

    if request.method == "POST":
        user_msg = request.form.get("question")
        if user_msg:
            ai_reply = get_ai_response_for_subject(user_msg, subject_id)
        else:
            ai_reply = "Please enter a question."

    return render_template("chat_subject.html", subject=subject, ai_reply=ai_reply, user_msg=user_msg)


# ==============================================================
# 🚀 RUN SERVER
# ==============================================================

if __name__ == "__main__":
    app.run(debug=True)
