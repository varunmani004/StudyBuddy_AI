# 🧠 StudyBuddy_AI

**StudyBuddy_AI** is a smart, offline AI-based learning assistant built using **Flask** and **MySQL**.  
It helps users learn smarter by allowing them to **upload study materials (PDFs, Docs)** and interact with them through an **AI-powered chat system** — even **without internet connectivity**.  
The system also provides **quizzes, flashcards**, and tracks the user’s **learning progress** across subjects.

---

## 🚀 Features

### 🔹 Phase 1: User Authentication
- Secure **User Registration** and **Login System**
- Password validation and encryption
- Session management using Flask sessions

### 🔹 Phase 2: Subject & File Management
- Create separate **subject sections** for organizing notes and files
- Upload **PDFs, DOCs**, and study materials
- Automatically store and retrieve file details from the database

### 🔹 Phase 2.5: File Upload and Storage System
- Upload, preview, and manage documents easily
- Organized storage system for user-specific files
- Backend handling using Flask and MySQL integration

### 🔹 Phase 3: Offline AI Chat System
- Chat with your uploaded files **locally**
- The AI processes text from PDFs and DOCs to answer questions
- Generate **quizzes**, **flashcards**, and summaries for revision
- Works offline using **locally stored models**

### 🔹 Phase 4: Learning Dashboard & Performance Tracking
- Personalized **dashboard** for each user
- Visual learning progress tracking
- Display uploaded subjects, documents, and quiz history
- User-friendly UI using **Bootstrap**

---

## 🧩 Tech Stack

| Layer | Technology Used |
|-------|------------------|
| 💻 Frontend | HTML, CSS, Bootstrap |
| ⚙️ Backend | Python (Flask Framework) |
| 🧠 AI Module | Local NLP model (Offline AI System) |
| 🗄️ Database | MySQL |
| 📦 Others | PyMySQL, PyPDF2, python-docx |

---

## 📁 Project Structure

StudyBuddy_AI/
│
├── app.py # Main Flask application
├── requirements.txt # Python dependencies
├── README.md # Project documentation
├── .gitignore # Files to ignore in Git
│
├── modules/ # Backend logic
│ ├── ai_module.py
│ ├── db_connection.py
│ └── pdf_handler.py
│
├── templates/ # HTML templates
│ ├── index.html
│ ├── login.html
│ ├── register.html
│ ├── dashboard.html
│ └── chat.html
│
├── static/ # CSS, JS, Images
│ ├── css/
│ ├── js/
│ └── images/
│
└── data/ # Uploaded study materials
├── subjects/
└── uploads/

📚 Future Enhancements

Integrate OpenAI API (optional for online version)

Add voice-based learning assistant

Mobile app version using Flutter or React Native

Analytics and report generation for student progress

🧑‍💻 Author

Varun V. M.
🎓 MCA Student | 💡 Aspiring Data Analyst & AI Developer
📍 Chennai, India
