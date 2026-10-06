# 🎓 Campus Connect 3.0

Campus Connect 3.0 is a modern, student-centric EdTech web application designed for colleges and universities. It unifies course study resources, real-time classmate communication, academic task planning, exam countdown reminders, doubt resolution with faculty, and campus circulars into a single responsive platform.

---

## ✨ Features

- **Personalized Student Dashboard**: Overview of tasks, exam countdowns, focus study statistics, and recent announcements.
- **Role-Based Authentication**: Custom portals and experiences for **Students**, **Faculty**, and **Clubs/Societies**.
- **Ask Planner**: Integrated daily task manager with priorities, due dates, and completion tracking.
- **Exam Reminders & Countdown**: Automated exam schedule countdown tracker.
- **Study Hub & Focus Timer**: Built-in Pomodoro focus timer with session logs and productivity tracking.
- **Classmates & Direct Chat**: Searchable directory of department peers and one-on-one direct messaging.
- **Lecture Notes Repository**: Upload and download departmental lecture slides and documents.
- **Ask Faculty (Doubts)**: Students can submit academic questions directly to faculty members.
- **Campus Notices**: Official college circulars and student club bulletins.
- **Assignments & Coursework**: Assignment deadline and submission tracker.
- **Quizzes**: Interactive department quizzes and performance results.

---

## 🛠️ Technology Stack

- **Backend**: Python / Flask
- **Database**: PostgreSQL (Production) / SQLite (Development) with Flask-SQLAlchemy
- **Frontend**: HTML5, Vanilla CSS3 (Custom SaaS Design System), Vanilla JavaScript
- **Deployment**: Vercel ready (`vercel.json`)

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/dishantpawar266-code/newcampusconnect.git
cd newcampusconnect
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and set your secret key and database URL:
```bash
cp .env.example .env
```

### 5. Run the development server
```bash
python app.py
```
Open your browser at `http://127.0.0.1:5000`.

---

## 📄 License
This project is for educational and campus use.
