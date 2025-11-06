from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.connection import get_db_connection

subject_bp = Blueprint('subject', __name__, url_prefix='/subjects')

# 📋 View all subjects
@subject_bp.route('/')
def subjects():
    if 'loggedin' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE user_id = %s", (user_id,))
    subjects = cursor.fetchall()
    conn.close()

    return render_template('subjects.html', subjects=subjects)

# ➕ Add new subject
@subject_bp.route('/add', methods=['POST'])
def add_subject():
    if 'loggedin' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))
    
    subject_name = request.form['subject_name']
    description = request.form.get('description', '')
    user_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subjects (user_id, subject_name, description) VALUES (%s, %s, %s)",
        (user_id, subject_name, description)
    )
    conn.commit()
    conn.close()

    flash("✅ Subject added successfully!", "success")
    return redirect(url_for('subject.subjects'))

# ✏️ Edit subject
@subject_bp.route('/edit/<int:subject_id>', methods=['POST'])
def edit_subject(subject_id):
    if 'loggedin' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    subject_name = request.form['subject_name']
    description = request.form.get('description', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subjects SET subject_name=%s, description=%s WHERE subject_id=%s",
        (subject_name, description, subject_id)
    )
    conn.commit()
    conn.close()

    flash("✏️ Subject updated successfully!", "success")
    return redirect(url_for('subject.subjects'))

# ❌ Delete subject
@subject_bp.route('/delete/<int:subject_id>')
def delete_subject(subject_id):
    if 'loggedin' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subjects WHERE subject_id = %s", (subject_id,))
    conn.commit()
    conn.close()

    flash("🗑️ Subject deleted successfully!", "info")
    return redirect(url_for('subject.subjects'))
