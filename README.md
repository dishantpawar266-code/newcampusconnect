# 🎓 Campus Connect 3.0

Campus Connect 3.0 is a modern, student-centric EdTech web application designed for colleges and universities. It unifies course study resources, real-time classmate communication, academic task planning, exam countdown reminders, doubt resolution with faculty, and campus circulars into a single responsive platform.

---

## ✨ Features

- **Personalized Student Dashboard**: Overview of tasks, exam countdowns, focus study statistics, and recent announcements.
- **Role-Based Authentication**: Custom portals and experiences for **Students**, **Faculty**, and **Clubs/Societies**.
- **Task Planner**: Integrated daily task manager with priorities, due dates, and completion tracking.
- **Exam Reminders & Countdown**: Automated exam schedule countdown tracker.
- **Study Hub & Focus Timer**: Built-in Pomodoro focus timer with session logs and productivity tracking.
- **Classmates & Direct Chat**: Searchable directory of department peers and one-on-one direct messaging.
- **Lecture Notes Repository**: Upload and download departmental lecture slides and documents (stored securely in DB).
- **Ask Faculty (Doubts)**: Students can submit academic questions directly to faculty members.
- **Campus Notices**: Official college circulars and student club bulletins.
- **Assignments & Coursework**: Assignment deadline and submission tracker.
- **Quizzes**: Interactive department quizzes and performance results.

---

## 🛠️ Technology Stack

- **Backend**: Python 3 / Flask
- **Database**: PostgreSQL (Production on Vercel) / SQLite (Local development) with Flask-SQLAlchemy
- **Frontend**: HTML5, Vanilla CSS3 (Custom SaaS Design System), Vanilla JavaScript
- **Deployment**: Serverless on Vercel (`api/index.py`, `vercel.json`)

---

## 🚀 Deploying to Vercel with Permanent PostgreSQL Database

> **⚠️ Critical Note on Vercel & SQLite**:  
> Vercel functions are serverless and have an ephemeral/read-only file system. Local SQLite (`.db`) cannot store data permanently on Vercel. To permanently store registered users, notes, doubts, and activity, a **cloud PostgreSQL database** (such as Neon, Supabase, or Vercel Postgres) is required.

### Step 1: Get a Free Cloud PostgreSQL Database (takes 1 minute)

Choose either **Neon** (recommended) or **Supabase**:

#### Option A: Neon (Fastest & Free)
1. Go to [https://neon.tech](https://neon.tech) and sign up for free (or use your GitHub account).
2. Create a new project (e.g. `campus-connect`).
3. Under the **Dashboard** / **Connection Details**, select **Connection string** (choose `PostgreSQL` or `psycopg2`).
4. Copy the URL. It looks like:
   ```text
   postgresql://dishant:Abc123xyz@ep-cool-flower-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

#### Option B: Supabase (Free)
1. Go to [https://supabase.com](https://supabase.com), create a free project.
2. In Project Settings > Database > Connection string (URI mode), copy the URL.

---

### Step 2: (Optional) Migrate Existing Local Users to PostgreSQL

If you already have users and data in your local SQLite database that you want transferred to your permanent cloud database:

```bash
# Run the migration script with your PostgreSQL connection URL
python migrate_to_postgres.py "postgresql://user:password@host/dbname?sslmode=require"
```
The script will automatically create all tables and migrate users, logs, study sessions, and all other records with 100% integrity.

---

### Step 3: Deploy to Vercel

#### Method 1: Deploy via GitHub (Recommended)
1. Push your code to your GitHub repository:
   ```bash
   git add .
   git commit -m "Configure Vercel deployment with permanent PostgreSQL database"
   git push origin main
   ```
2. Open the [Vercel Dashboard](https://vercel.com/dashboard) and click **"Add New..." > "Project"**.
3. Import your GitHub repository (`dishantpawar266-code/newcampusconnect`).
4. In the **Environment Variables** section, add the following variables:
   - `DATABASE_URL` = `postgresql://user:password@host/dbname?sslmode=require` (your Neon / Supabase URL)
   - `FLASK_SECRET_KEY` = `a-random-secure-string-at-least-32-chars`
   - `ADMIN_EMAIL` = `admin@campusconnect.edu`
   - `ADMIN_PASSWORD` = `YourSecureAdminPassword`
   - `FLASK_ENV` = `production`
5. Click **"Deploy"**.

#### Method 2: Deploy via Vercel CLI
```bash
# Install Vercel CLI globally
npm i -g vercel

# Run vercel deploy
vercel

# Add environment variables
vercel env add DATABASE_URL
vercel env add FLASK_SECRET_KEY
vercel env add ADMIN_EMAIL
vercel env add ADMIN_PASSWORD

# Deploy to production
vercel --prod
```

---

## 💻 Local Development

### 1. Clone & Setup
```bash
git clone https://github.com/dishantpawar266-code/newcampusconnect.git
cd newcampusconnect
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Run Development Server
```bash
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## 📄 License
Educational & Campus Use Only.
