from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta

# Initialize Flask and extensions
app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key_here"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    chem_progress = db.Column(db.Integer, default=0)
    bio_y13_progress = db.Column(db.Integer, default=0)
    bio_y12_progress = db.Column(db.Integer, default=0)
    subjects = db.relationship('UserSubjects', backref='user', uselist=False)

class UserSubjects(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chemistry = db.Column(db.Boolean, default=False)
    biology = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------
# Sample Data for Timetable & Weekend Tasks
# ---------------------------
weekday_timetable = {
    "Monday": [
        "Psychology: Research Methods & Approaches",
        "Chemistry: Up Learn session (1-2 lessons; review current concepts)",
        "Biology (Y13): Up Learn session (1-2 lessons; focus on retention)",
    ],
    "Tuesday": [
        "Psychology: Memory & Attachment",
        "Chemistry: Up Learn session (1-2 new lessons on challenging topics)",
        "Biology (Y13): Continue progress & review weak areas",
    ],
    "Wednesday": [
        "Psychology: Psychopathology & Biopsychology",
        "Chemistry: Review previous lessons or new lesson (problem-solving practice)",
        "Biology (Y12): Start Up Learn lessons for Year 12 topics",
    ],
    "Thursday": [
        "Psychology: Issues & Debates, Schizophrenia",
        "Chemistry: Up Learn session (focus on Physical Chemistry: Acids, Bases, Redox)",
        "Biology (Y13): Up Learn session (continue Year 13 topics)",
    ],
}

weekend_tasks = [
    {"task": "Chemistry: Complete one Up Learn lesson and review areas of confusion", "points": 3},
    {"task": "Chemistry: Do past paper questions on a specific topic", "points": 4},
    {"task": "Chemistry: Watch/review a Chemistry video/summary and take notes", "points": 2},
    {"task": "Biology: Complete 1-2 Up Learn lessons (Year 12 or 13)", "points": 3},
    {"task": "Biology: Practice questions or flashcards based on recent lessons", "points": 4},
    {"task": "Biology: Review concepts (e.g., cell division, genetics)", "points": 2},
    {"task": "Psychology: Complete an essay-style question on a major topic", "points": 4},
    {"task": "Psychology: Review case studies or specific theories", "points": 3},
    {"task": "Psychology: Take a timed quiz on topics", "points": 3},
]

# Add subject end dates
SUBJECT_END_DATES = {
    'Psychology': '2024-06-15',
    'Chemistry': '2024-06-20',
    'Biology_Y13': '2024-06-25',
    'Biology_Y12': '2024-05-30'
}

def get_calendar_data(start_date=None):
    if not start_date:
        start_date = datetime.now()
    
    weeks = []
    current_date = start_date
    
    for week in range(1, 16):  # Generate 15 weeks of data
        week_data = {
            'week_number': week,
            'start_date': current_date.strftime('%Y-%m-%d'),
            'end_date': (current_date + timedelta(days=6)).strftime('%Y-%m-%d'),
            'subjects': {}
        }
        
        for subject, end_date in SUBJECT_END_DATES.items():
            if current_date.strftime('%Y-%m-%d') <= end_date:
                week_data['subjects'][subject] = {
                    'tasks': weekday_timetable.get(current_date.strftime('%A'), []),
                    'end_date': end_date
                }
        
        weeks.append(week_data)
        current_date += timedelta(days=7)
    
    return weeks

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for("register"))
        new_user = User(
            username=username,
            password=generate_password_hash(password, method="pbkdf2:sha256"),
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.")
        return redirect(url_for("login"))
    return render_template("register.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")
    return render_template("login.html")

# Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# Dashboard: Shows timetable, weekend points system, & Up Learn progress tracker
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    message = None
    if request.method == "POST":
        # Only process if it's an actual form submission
        if "update_progress" in request.form:
            try:
                # Check if values have actually changed
                new_chem = int(request.form.get("chem_progress", 0))
                new_bio_y13 = int(request.form.get("bio_y13_progress", 0))
                new_bio_y12 = int(request.form.get("bio_y12_progress", 0))
                
                if (new_chem != current_user.chem_progress or 
                    new_bio_y13 != current_user.bio_y13_progress or 
                    new_bio_y12 != current_user.bio_y12_progress):
                    
                    current_user.chem_progress = new_chem
                    current_user.bio_y13_progress = new_bio_y13
                    current_user.bio_y12_progress = new_bio_y12
                    db.session.commit()
                    message = "Progress updated successfully!"
            except Exception as e:
                message = "Error updating progress. Please check your inputs."
    
    calendar_data = get_calendar_data()
    return render_template(
        "dashboard.html",
        user=current_user,
        timetable=weekday_timetable,
        tasks=weekend_tasks,
        message=message,
        calendar_data=calendar_data,
        subject_end_dates=SUBJECT_END_DATES
    )

# Endpoint to log weekend points
@app.route("/log_points", methods=["POST"])
@login_required
def log_points():
    selected_tasks = request.form.getlist("tasks")
    total_points = 0
    for task_index in selected_tasks:
        try:
            idx = int(task_index)
            if 0 <= idx < len(weekend_tasks):
                total_points += weekend_tasks[idx]["points"]
        except ValueError:
            continue
    flash(f"You earned {total_points} points today!")
    return redirect(url_for("dashboard"))

@app.route("/update_subjects", methods=["POST"])
@login_required
def update_subjects():
    if not current_user.subjects:
        subjects = UserSubjects(user_id=current_user.id)
        db.session.add(subjects)
    else:
        subjects = current_user.subjects
    
    subjects.chemistry = request.form.get("chemistry") == "on"
    subjects.biology = request.form.get("biology") == "on"
    
    db.session.commit()
    flash("Subjects updated successfully!")
    return redirect(url_for("dashboard"))

# Add a new route for curriculum
@app.route("/curriculum")
@login_required
def curriculum():
    # Simply render the curriculum template (no need for initial_view flag anymore)
    return render_template("curriculum.html")

def init_db():
    """Initialize the database only if it doesn't exist"""
    db_path = "site.db"
    if not os.path.exists(db_path):
        with app.app_context():
            db.create_all()
            print("Database initialized for the first time!")

if __name__ == "__main__":
    # Create database only if it doesn't exist
    init_db()
    app.run(debug=True)
