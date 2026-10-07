"""
Campus Connect 3.0 — Student Resource Hub Data
Structured database of verified, high-utility academic, coding, career, and AI resources.
"""

RESOURCES_DATA = [
    # ---------------------------------------------------------
    # College / Student Resources (Spotlight + Official)
    # ---------------------------------------------------------
    {
        "id": "rcpit-official",
        "name": "RCPIT Official Website",
        "category": "College",
        "url": "https://www.rcpit.ac.in/",
        "icon": "🏛️",
        "badge": "Official Portal",
        "description": "Official website of R. C. Patel Institute of Technology (RCPIT), Shirpur. Access college notifications, academic calendar, department updates, syllabus, exam circulars, and campus events.",
        "tags": ["rcpit", "college", "official", "shirpur", "academics", "portal", "syllabus", "notifications"],
        "is_recommended": True
    },
    {
        "id": "campus-credentials",
        "name": "Campus Credentials",
        "category": "College",
        "url": "https://learn.campuscredentials.com/",
        "icon": "🏅",
        "badge": "Official Partner",
        "description": "Student learning and assessment portal for campus training programs, skill evaluation, tests, and verified digital credentials.",
        "tags": ["credentials", "learning", "assessments", "training", "certificates", "badges", "college", "official"],
        "is_recommended": True,
        "is_spotlight": True
    },
    {
        "id": "swayam-nptel",
        "name": "SWAYAM / NPTEL",
        "category": "College",
        "url": "https://swayam.gov.in/",
        "icon": "🎓",
        "badge": "IIT Certified",
        "description": "Online certified courses taught by IIT and IISc professors with college credit-transfer options and proctored examination certificates.",
        "tags": ["nptel", "swayam", "iit courses", "credit transfer", "certification", "engineering", "college"],
        "is_recommended": True
    },

    # ---------------------------------------------------------
    # Academic & Coding
    # ---------------------------------------------------------
    {
        "id": "leetcode",
        "name": "LeetCode",
        "category": "Coding",
        "url": "https://leetcode.com",
        "icon": "⚡",
        "badge": "Interview Prep",
        "description": "The gold-standard platform for practicing Data Structures & Algorithms, mock technical interviews, and preparation for top product-based tech companies.",
        "tags": ["coding", "dsa", "algorithms", "interview prep", "data structures", "c++", "java", "python"],
        "is_recommended": True
    },
    {
        "id": "codechef",
        "name": "CodeChef",
        "category": "Coding",
        "url": "https://www.codechef.com",
        "icon": "👨‍💻",
        "badge": "Contests",
        "description": "Competitive programming platform offering weekly Starters contests, Cook-Offs, and rated algorithmic challenges for college students.",
        "tags": ["coding", "competitive programming", "algorithms", "contests", "dsa", "rankings"],
        "is_recommended": True
    },
    {
        "id": "hackerrank",
        "name": "HackerRank",
        "category": "Coding",
        "url": "https://www.hackerrank.com",
        "icon": "🟢",
        "badge": "Skills Test",
        "description": "Practice language fundamentals, problem solving, SQL, and earn industry-recognized skill assessment badges for your resume.",
        "tags": ["coding", "practice", "sql", "certifications", "python", "cpp", "java", "fundamentals"],
        "is_recommended": False
    },
    {
        "id": "geeksforgeeks",
        "name": "GeeksforGeeks",
        "category": "Coding",
        "url": "https://www.geeksforgeeks.org",
        "icon": "📚",
        "badge": "CS Library",
        "description": "Comprehensive computer science portal featuring extensive DSA tutorials, core engineering subject notes, and real campus interview experiences.",
        "tags": ["dsa", "cs fundamentals", "interview questions", "tutorials", "notes", "dbms", "os", "computer networks"],
        "is_recommended": True
    },
    {
        "id": "github",
        "name": "GitHub",
        "category": "Coding",
        "url": "https://github.com",
        "icon": "🐙",
        "badge": "Essential",
        "description": "The world's leading developer platform. Host your project code, build your portfolio, contribute to open source, and utilize the GitHub Student Developer Pack.",
        "tags": ["git", "open source", "collaboration", "repositories", "version control", "portfolio", "projects"],
        "is_recommended": True
    },

    # ---------------------------------------------------------
    # Web & Documentation
    # ---------------------------------------------------------
    {
        "id": "w3schools",
        "name": "W3Schools",
        "category": "Web & Docs",
        "url": "https://www.w3schools.com",
        "icon": "🌐",
        "badge": "Beginner Friendly",
        "description": "Interactive, clean reference tutorials and live editors for web technologies including HTML, CSS, JavaScript, SQL, and Python basics.",
        "tags": ["web development", "html", "css", "javascript", "sql", "tutorials", "web"],
        "is_recommended": False
    },
    {
        "id": "mdn-docs",
        "name": "MDN Web Docs",
        "category": "Web & Docs",
        "url": "https://developer.mozilla.org",
        "icon": "📖",
        "badge": "Standard Docs",
        "description": "Mozilla's authoritative web development documentation covering HTML5, CSS3, modern JavaScript specifications, and Web APIs in complete detail.",
        "tags": ["javascript", "html5", "css3", "web standards", "documentation", "frontend", "apis"],
        "is_recommended": True
    },
    {
        "id": "python-docs",
        "name": "Python Documentation",
        "category": "Web & Docs",
        "url": "https://docs.python.org/3/",
        "icon": "🐍",
        "badge": "Official Docs",
        "description": "Official Python 3 reference library, standard module documentation, language grammar specifications, and introductory tutorials.",
        "tags": ["python", "documentation", "official docs", "libraries", "modules", "backend"],
        "is_recommended": True
    },
    {
        "id": "java-docs",
        "name": "Java Documentation (Oracle)",
        "category": "Web & Docs",
        "url": "https://docs.oracle.com/en/java/",
        "icon": "☕",
        "badge": "Official Docs",
        "description": "Complete Java SE documentation, API specification guides, JVM architecture notes, and enterprise development resources.",
        "tags": ["java", "jdk", "api reference", "documentation", "oop", "jvm"],
        "is_recommended": False
    },
    {
        "id": "cpp-reference",
        "name": "C/C++ Reference",
        "category": "Web & Docs",
        "url": "https://en.cppreference.com/w/",
        "icon": "⚙️",
        "badge": "Core Systems",
        "description": "Exhaustive modern C and C++ standard library reference, memory management guides, STL containers, and algorithmic complexity notes.",
        "tags": ["c++", "c", "cpp", "stl", "algorithms", "memory", "pointers", "systems"],
        "is_recommended": False
    },

    # ---------------------------------------------------------
    # Career & Opportunities
    # ---------------------------------------------------------
    {
        "id": "unstop",
        "name": "Unstop",
        "category": "Career",
        "url": "https://unstop.com",
        "icon": "🚀",
        "badge": "Competitions",
        "description": "Discover national engineering hackathons, college tech fests, hiring quizzes, case competitions, and campus ambassadorship programs.",
        "tags": ["hackathons", "competitions", "internships", "jobs", "quizzes", "campus hiring", "career"],
        "is_recommended": True
    },
    {
        "id": "internshala",
        "name": "Internshala",
        "category": "Career",
        "url": "https://internshala.com",
        "icon": "💼",
        "badge": "Internships",
        "description": "Find summer internships, work-from-home roles, and entry-level technical jobs with verified stipends across leading companies and startups.",
        "tags": ["internships", "student jobs", "summer internships", "work from home", "stipends", "career"],
        "is_recommended": True
    },
    {
        "id": "linkedin-jobs",
        "name": "LinkedIn Jobs",
        "category": "Career",
        "url": "https://www.linkedin.com/jobs/",
        "icon": "👔",
        "badge": "Placements",
        "description": "Browse entry-level tech roles, software engineering internships, connect with alumni recruiters, and set up job alert notifications.",
        "tags": ["networking", "jobs", "placements", "careers", "recruitment", "software engineer"],
        "is_recommended": True
    },
    {
        "id": "aicte-internships",
        "name": "AICTE Internship Portal",
        "category": "Career",
        "url": "https://internship.aicte-india.org/",
        "icon": "🏛️",
        "badge": "Government",
        "description": "Official Ministry of Education portal offering verified internships with Smart Cities, NHAI, state governments, and corporate CSR partners.",
        "tags": ["aicte", "government internships", "engineering", "ministry of education", "public sector"],
        "is_recommended": True
    },
    {
        "id": "nats-portal",
        "name": "NATS Apprenticeship Portal",
        "category": "Career",
        "url": "https://nats.education.gov.in/",
        "icon": "🇮🇳",
        "badge": "Govt Stipend",
        "description": "Government of India national apprenticeship training scheme for engineering diploma and degree graduates with monthly direct stipends.",
        "tags": ["government", "apprenticeship", "training", "ministry", "stipend", "psu"],
        "is_recommended": False
    },
    {
        "id": "devfolio",
        "name": "Devfolio",
        "category": "Career",
        "url": "https://devfolio.co",
        "icon": "💡",
        "badge": "Hackathons",
        "description": "The premier community for builders and collegiate hackathons. Apply to top student hackathons, showcase builds, and win cash prizes.",
        "tags": ["hackathons", "builder", "web3", "ai hackathons", "projects", "community"],
        "is_recommended": True
    },

    # ---------------------------------------------------------
    # Learning & AI / ML
    # ---------------------------------------------------------
    {
        "id": "kaggle",
        "name": "Kaggle",
        "category": "AI & ML",
        "url": "https://www.kaggle.com",
        "icon": "📊",
        "badge": "Data Science",
        "description": "The home of data science and machine learning. Access 50,000+ real-world datasets, free GPU Jupyter notebooks, and competitive ML tournaments.",
        "tags": ["machine learning", "data science", "datasets", "deep learning", "python", "jupyter", "ai"],
        "is_recommended": True
    },
    {
        "id": "huggingface",
        "name": "Hugging Face",
        "category": "AI & ML",
        "url": "https://huggingface.co",
        "icon": "🤗",
        "badge": "Open AI",
        "description": "The collaborative platform for open-source AI. Explore open-weights LLMs, computer vision models, fine-tuned checkpoints, and live Gradio Spaces.",
        "tags": ["ai", "transformers", "llm", "deep learning", "models", "nlp", "genai"],
        "is_recommended": True
    },
    {
        "id": "google-ai",
        "name": "Google AI & Developers",
        "category": "AI & ML",
        "url": "https://developers.google.com/machine-learning",
        "icon": "🤖",
        "badge": "Google ML",
        "description": "Free Machine Learning Crash Course by Google engineers, TensorFlow guides, JAX frameworks, and practical generative AI labs.",
        "tags": ["google ai", "tensorflow", "machine learning crash course", "deep learning", "google"],
        "is_recommended": True
    },
    {
        "id": "microsoft-learn",
        "name": "Microsoft Learn",
        "category": "AI & ML",
        "url": "https://learn.microsoft.com",
        "icon": "☁️",
        "badge": "Cloud & AI",
        "description": "Interactive learning modules, Azure AI engineer paths, free sandbox labs, and exam preparations for global Microsoft certifications.",
        "tags": ["cloud", "azure", "certifications", "dotnet", "ai engineer", "microsoft"],
        "is_recommended": False
    },
    {
        "id": "aws-skillbuilder",
        "name": "AWS Skill Builder",
        "category": "AI & ML",
        "url": "https://explore.skillbuilder.aws/",
        "icon": "📦",
        "badge": "Cloud Training",
        "description": "Amazon Web Services digital training center with 600+ free digital courses in cloud architecture, DevOps, serverless, and cloud security.",
        "tags": ["aws", "cloud", "devops", "cloud computing", "solutions architect", "amazon"],
        "is_recommended": False
    },
    {
        "id": "nvidia-dli",
        "name": "NVIDIA Deep Learning Institute",
        "category": "AI & ML",
        "url": "https://www.nvidia.com/en-us/training/",
        "icon": "🖥️",
        "badge": "GPU Computing",
        "description": "Official GPU accelerated computing labs, CUDA programming, transformer model optimization, and autonomous systems training.",
        "tags": ["nvidia", "cuda", "gpu", "deep learning", "computer vision", "acceleration"],
        "is_recommended": True
    },
    {
        "id": "deeplearning-ai",
        "name": "DeepLearning.AI",
        "category": "AI & ML",
        "url": "https://www.deeplearning.ai",
        "icon": "🧠",
        "badge": "Andrew Ng",
        "description": "World-famous Machine Learning Specialization and short courses on LangChain, Prompt Engineering, RAG architectures, and AI Agents.",
        "tags": ["deep learning", "ai", "andrew ng", "neural networks", "genai", "prompt engineering", "rag"],
        "is_recommended": True
    }
]

CATEGORIES = [
    {"id": "all", "name": "All Resources", "icon": "🌐"},
    {"id": "bookmarks", "name": "⭐ My Resources", "icon": "⭐"},
    {"id": "Coding", "name": "Coding & DSA", "icon": "💻"},
    {"id": "Career", "name": "Career & Internships", "icon": "💼"},
    {"id": "AI & ML", "name": "AI & Machine Learning", "icon": "🤖"},
    {"id": "College", "name": "College Portals", "icon": "🎓"},
    {"id": "Web & Docs", "name": "Web & Dev Docs", "icon": "📖"}
]

def get_all_resources():
    return RESOURCES_DATA

def get_recommended_resources():
    return [r for r in RESOURCES_DATA if r.get("is_recommended")]

def get_spotlight_resource():
    for r in RESOURCES_DATA:
        if r.get("is_spotlight"):
            return r
    return None
