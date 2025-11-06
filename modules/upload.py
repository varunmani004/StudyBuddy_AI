# modules/upload.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
import os

upload_bp = Blueprint('upload_bp', __name__, template_folder='../templates')

@upload_bp.route('/upload_extra', methods=['GET'])
def upload_extra():
    """Example endpoint if you want an alternate upload page."""
    return render_template("upload.html")

@upload_bp.route('/upload_extra', methods=['POST'])
def upload_extra_post():
    """Example POST upload route."""
    if 'file' not in request.files:
        flash("No file part!", "warning")
        return redirect(url_for('upload_bp.upload_extra'))

    file = request.files['file']
    if file.filename == '':
        flash("No file selected!", "danger")
        return redirect(url_for('upload_bp.upload_extra'))

    save_dir = os.path.join("static", "uploads", "extras")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, file.filename)
    file.save(save_path)
    flash(f"✅ File saved to {save_path}", "success")
    return redirect(url_for('upload_bp.upload_extra'))
