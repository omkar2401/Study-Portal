# 📚 Study Material & MCQ Practice Portal

## 📌 Project Overview

The **Study Material & MCQ Practice Portal** is a web-based learning application developed using Python Flask, SQLite, HTML, CSS, and JavaScript. It provides a centralized platform where administrators can upload PDF study materials and prepare multiple-choice questions (MCQs) for students.

The application integrates AI-powered question generation to create draft MCQs from the text extracted from uploaded PDFs. Students can register, log in, access published study materials, practice quizzes, receive instant feedback, and track their quiz results.

The main objective of this project is to make learning more interactive, accessible, and effective through digital study resources and automated quiz practice.

## 🎯 Objectives

- Provide separate login and dashboards for administrators and students.
- Allow administrators to upload and manage PDF study materials.
- Generate MCQs automatically from PDF content using AI.
- Allow administrators to create questions manually and review AI-generated questions.
- Provide instant feedback on students' selected answers.
- Display the correct answer when a student selects an incorrect option.
- Record quiz scores and maintain a history of student attempts.
- Simplify the process of preparing study materials and conducting online practice tests.

## ✨ Features

### 👨‍💼 Admin Module

- Secure admin login.
- Upload PDF study materials with titles, subjects, and descriptions.
- Extract selectable text from uploaded PDFs.
- Generate draft MCQs using AI.
- Create questions manually.
- Edit questions, options, explanations, and correct answers.
- Publish or unpublish questions for students.
- Delete questions and manage study materials.
- View the number of materials, questions, and registered students.

### 🎓 Student Module

- Student registration and login.
- Access published study materials.
- Open and read uploaded PDF files.
- Practice MCQs with four options: A, B, C, and D.
- Receive feedback after submitting answers.
- View the correct answer for each question.
- Read explanations when available.
- View quiz scores and percentages.
- Review previous quiz attempts.

### 🤖 AI-Powered MCQ Generation

- Extract text from uploaded PDF documents.
- Generate multiple-choice questions using the OpenAI API.
- Provide four answer options for each generated question.
- Identify the proposed correct answer.
- Generate explanations where supported by the source content.
- Allow administrators to review and edit generated questions before publishing.

**Note:** AI-generated questions may contain errors and should be checked by the administrator before publication. Scanned, image-only PDFs require OCR, which is not included in the current version.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Flask | Web application framework |
| SQLite | Database for users, materials, questions, and quiz results |
| HTML5 | Web page structure |
| CSS3 | Styling and responsive layouts |
| JavaScript | Client-side interactions and quiz progress |
| PyMuPDF | Extracting text from PDF documents |
| OpenAI API | AI-powered MCQ generation |
| Werkzeug | Password hashing and secure file handling |
| python-dotenv | Loading environment variables |

## 🏗️ Application Architecture

1. The administrator logs in and uploads a PDF.
2. The application extracts selectable text from the PDF.
3. The administrator generates MCQs using AI or creates questions manually.
4. The administrator reviews the questions and publishes them.
5. Students register and log in to the portal.
6. Students read the study materials and attempt published quizzes.
7. The application evaluates answers and displays the correct options.
8. Quiz scores and attempt history are stored in SQLite.

## 📂 Project Structure

```text
study_material_mcq_portal/
│
├── app.py                  # Flask application and routes
├── portal.db               # SQLite database (created at runtime)
├── requirements.txt        # Python dependencies
├── .env                    # Local configuration and API key
├── .env.example            # Example environment configuration
├── .gitignore              # Files excluded from Git
│
├── uploads/                # Uploaded PDF study materials
│   └── .gitkeep
│
├── templates/              # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── admin_dashboard.html
│   ├── upload_material.html
│   ├── material_detail.html
│   ├── question_form.html
│   ├── student_dashboard.html
│   ├── student_material.html
│   ├── quiz.html
│   ├── quiz_result.html
│   ├── student_results.html
│   └── error.html
│
└── static/
    ├── style.css           # Application styles
    └── app.js              # Client-side JavaScript
```

## ⚙️ Installation and Setup

### Prerequisites

- Windows 10 or Windows 11
- Python 3.13 recommended for this project setup
- Visual Studio Code
- Internet connection for installing dependencies and using AI question generation
- An OpenAI API key for AI-powered MCQ generation

### Step 1: Download the Project

Download or clone the project repository and extract it into a folder on your computer.

Open the extracted project folder in Visual Studio Code.

### Step 2: Create a Virtual Environment

Open the VS Code terminal and run:

```powershell
py -3.13 -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

Run:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file by copying `.env.example`:

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure the values:

```env
FLASK_SECRET_KEY=replace-with-a-long-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ChangeMe123!
ADMIN_EMAIL=admin@example.com

OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

Replace the example API key with your own valid key. Keep the `.env` file private and never commit it to GitHub.

AI generation requires an OpenAI API key and may incur usage charges. Manual question creation and the main portal features can work without the AI key.

### Step 5: Run the Application

Start the Flask server:

```powershell
python app.py
```

Open your browser and visit:

**http://127.0.0.1:5000**

Keep the terminal open while using the application.

## 🔐 Login and User Registration

### Admin Login

The application creates the initial administrator account using the `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_EMAIL` values in `.env` when the database is initialized for the first time.

Example initial credentials:

- Username: `admin`
- Password: `ChangeMe123!`

Change the example password before your first run. Updating `.env` later does not automatically change an existing admin password.

### Student Login

1. Open the application in your browser.
2. Select **Student registration**.
3. Enter a username, email address, and password.
4. Register and return to the login page.
5. Log in using your new credentials.

Students can access materials and quizzes after the administrator publishes the relevant questions.

## 📝 How to Use the Application

### Admin Workflow

1. Log in to the admin dashboard.
2. Select **Upload PDF**.
3. Enter the title, subject, and optional description.
4. Upload a PDF file.
5. Open the uploaded material.
6. Select the number of MCQs to generate.
7. Click **Generate MCQs** or choose **Add question manually**.
8. Review and edit the questions and answer keys.
9. Publish the questions for students.

### Student Workflow

1. Register a student account.
2. Log in to the portal.
3. Open an available study material.
4. Read the PDF.
5. Start the quiz and select answers.
6. Submit the quiz to view feedback, correct answers, and explanations.
7. Review scores and previous attempts in **My results**.

## 🗄️ Database Design

The application uses SQLite and includes four main tables:

- **users:** Stores usernames, email addresses, password hashes, roles, and registration timestamps.
- **materials:** Stores study material metadata, PDF filenames, extracted text, and upload information.
- **questions:** Stores questions, four answer options, the correct option, explanations, and publication status.
- **attempts:** Stores student quiz scores, total questions, submitted answers, and attempt timestamps.

The database file is created automatically when the Flask application initializes.

## 🔒 Security Considerations

- Passwords are stored as hashes rather than plain text.
- Admin and student routes use role-based access checks.
- Uploaded files are restricted to PDF extensions and a 20 MB upload limit.
- API keys and configuration secrets should be stored in `.env`.
- The `.env`, database, and uploaded PDFs should not be committed to a public repository.
- AI-generated questions should be reviewed before being published.

This is a local development project. Additional security measures are needed before deploying it publicly, including HTTPS, CSRF protection, rate limiting, production secret management, secure hosting, and database backups.

## 🚀 Future Enhancements

- OCR support for scanned PDFs.
- Subject-wise quizzes and difficulty levels.
- Quiz timers and negative marking.
- Randomized questions and answer options.
- Student leaderboards and performance analytics.
- Downloadable score reports.
- Admin-managed student accounts.
- Email-based password recovery.
- Improved AI question validation and duplicate detection.
- Cloud deployment and support for multiple institutions.

## 🎓 Project Outcome

The Study Material & MCQ Practice Portal demonstrates how a web application can combine authentication, database management, document processing, AI integration, and interactive quizzes to support digital learning.

It provides administrators with a convenient way to manage study materials and questions while enabling students to practice, receive feedback, and monitor their learning progress.

## 👨‍💻 Author

**Project:** Study Material & MCQ Practice Portal  
**Backend:** Python Flask  
**Database:** SQLite  
**Frontend:** HTML, CSS, JavaScript  
**AI Integration:** OpenAI API
