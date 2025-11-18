# text_extraction.py
import os
from pypdf import PdfReader
from docx import Document

def extract_text(file_path, subject_id):
    """
    Extract text from PDF, DOCX, or TXT.
    Save it inside:
        static/uploads/processed_texts/<subject_id>/<filename>.txt
    Return full processed text output path.
    """
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    # -------------------------------
    # Extract based on file type
    # -------------------------------
    if ext == ".pdf":
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

    elif ext == ".docx":
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf8", errors="ignore") as f:
            text = f.read()

    else:
        print(f"[!] Unsupported file format: {ext}")
        return None

    # ---------------------------------------
    # Save to subject folder
    # ---------------------------------------
    processed_dir = os.path.join(
        "static", "uploads", "processed_texts", str(subject_id)
    )
    os.makedirs(processed_dir, exist_ok=True)

    base_name = os.path.basename(file_path).replace(ext, ".txt")
    output_path = os.path.join(processed_dir, base_name)

    with open(output_path, "w", encoding="utf8") as out:
        out.write(text.strip())

    print(f"[+] Text extracted → {output_path}")
    return output_path
