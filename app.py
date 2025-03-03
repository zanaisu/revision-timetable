import os
import sys
import subprocess
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import random

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key_here" 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Custom Jinja filters
def days_until_filter(date_str):
    """Calculate days remaining until a specific date"""
    try:
        end_date = datetime.strptime(date_str, '%Y-%m-%d')
        days_left = (end_date - datetime.now()).days
        return max(0, days_left)  # Ensure we don't return negative days
    except:
        return 0

def format_date_filter(date_str, format_str):
    """Format a date string to a different format"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime(format_str)
    except:
        return date_str

# Register custom filters
app.jinja_env.filters['days_until'] = days_until_filter
app.jinja_env.filters['format_date'] = format_date_filter

# -------------------------
# Database Models
# -------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    chem_progress = db.Column(db.Integer, default=0)
    bio_y13_progress = db.Column(db.Integer, default=0)
    bio_y12_progress = db.Column(db.Integer, default=0)
    onboarding_step = db.Column(db.Integer, default=0)
    daily_study_hours = db.Column(db.Float, default=4.0)
    subjects = db.relationship('UserSubjects', backref='user', uselist=False)
    task_logs = db.relationship('TaskLog', backref='user', lazy=True)
    uplearn_logs = db.relationship('UplearnLog', backref='user', lazy=True)
    topic_proficiencies = db.relationship('TopicProficiency', backref='user', lazy=True)

class UserSubjects(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chemistry = db.Column(db.Boolean, default=False)
    biology = db.Column(db.Boolean, default=False)

class TaskLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    date_completed = db.Column(db.DateTime, default=datetime.now)
    duration = db.Column(db.Integer)  # Duration in minutes
    difficulty = db.Column(db.Integer)  # Scale of 1-5
    notes = db.Column(db.Text)
    
class UplearnLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=False)  # Chemistry, Biology Y12, Biology Y13
    date = db.Column(db.Date, default=datetime.now().date)
    lessons_completed = db.Column(db.Integer, default=0)
    time_spent = db.Column(db.Integer)  # Time in minutes
    comprehension = db.Column(db.Integer)  # Scale of 1-5

class TopicProficiency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=False)  # Chemistry, Biology, Psychology
    topic = db.Column(db.String(100), nullable=False)  # The topic name from curriculum.json
    proficiency = db.Column(db.Integer, nullable=False)  # Scale of 1-5
    last_updated = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    notes = db.Column(db.Text)  # Optional notes about proficiency
    
    # Add a composite unique constraint to ensure one rating per user/subject/topic
    __table_args__ = (db.UniqueConstraint('user_id', 'subject', 'topic', name='uix_user_subject_topic'),)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# -------------------------
# Helper Functions
# -------------------------
def load_curriculum():
    """Load curriculum data from JSON file"""
    file_path = os.path.join(app.static_folder, 'data', 'curriculum.json')
    
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find curriculum.json at {file_path}")
        # Return empty curriculum structure as fallback
        return {
            "Biology": {"Years": []},
            "Chemistry": {"Modules": []},
            "Psychology": {"Papers": []}
        }

def generate_task_for_topic(subject, topic, duration_minutes):
    """Generate a study task for a specific topic"""
    task_templates = [
        {"type": "Review", "template": "Review and create summary notes on {topic}", "min_duration": 30},
        {"type": "Practice", "template": "Complete practice questions on {topic}", "min_duration": 45},
        {"type": "Quiz", "template": "Create and answer quiz questions for {topic}", "min_duration": 20},
        {"type": "Mind Map", "template": "Create a detailed mind map for {topic}", "min_duration": 25},
        {"type": "Flash Cards", "template": "Make flash cards covering {topic}", "min_duration": 30},
        {"type": "Essay Plan", "template": "Create essay plans related to {topic}", "min_duration": 40},
        {"type": "Uplearn", "template": "Complete Uplearn session on {topic}", "min_duration": 45}
    ]
    
    suitable_templates = [t for t in task_templates if t["min_duration"] <= duration_minutes]
    if not suitable_templates:
        suitable_templates = task_templates
    
    template = random.choice(suitable_templates)
    return {
        "subject": subject,
        "task": template["template"].format(topic=topic["Title"]),
        "duration": duration_minutes,
        "type": template["type"]
    }

def generate_daily_tasks(curriculum_data, user_subjects=None, uplearn_subjects=None, user_proficiencies=None):
    """Generate daily study tasks based on user preferences and curriculum"""
    total_daily_minutes = random.randint(180, 240)  # 3-4 hours
    minutes_remaining = total_daily_minutes
    tasks = []
    
    # Select subjects based on user preference or randomly
    if user_subjects and len(user_subjects) > 0:
        daily_subjects = [s for s in user_subjects if s in curriculum_data]
        if not daily_subjects and curriculum_data:
            daily_subjects = [list(curriculum_data.keys())[0]]
    else:
        subjects = list(curriculum_data.keys())
        daily_subjects = random.sample(subjects, min(random.randint(2, 3), len(subjects)))
    
    # Weight topics based on proficiency if available
    weighted_topics = {}
    if user_proficiencies:
        # Dictionary to store topic weights by subject
        # Lower proficiency means higher weight (more likely to be selected)
        for subject in daily_subjects:
            if subject in user_proficiencies:
                subject_proficiencies = user_proficiencies[subject]
                weighted_topics[subject] = {}
                for topic, proficiency in subject_proficiencies.items():
                    # Invert proficiency: lower proficiency = higher weight
                    # 1 (beginner) = weight 5
                    # 5 (expert) = weight 1
                    weighted_topics[subject][topic] = 6 - proficiency  # Invert the scale
    
    for subject in daily_subjects:
        # Allocate time based on remaining minutes
        subject_minutes = minutes_remaining // len(daily_subjects)
        
        # Skip if subject is not in curriculum data
        if subject not in curriculum_data:
            continue
            
        subject_data = curriculum_data[subject]
        
        # Determine if this subject should be Uplearn-oriented
        is_uplearn_task = False
        if uplearn_subjects and subject in uplearn_subjects and subject != "Psychology" and random.random() < 0.9:
            is_uplearn_task = True
        
        if subject == "Biology":
            # Handle Biology's special structure with Years
            for year in subject_data["Years"]:
                for module in year["Modules"]:
                    if module["Topics"]:
                        # Select topic with weighting if available
                        if subject in weighted_topics and weighted_topics[subject]:
                            # Find topics from this module that have proficiency ratings
                            module_topics = {}
                            for topic in module["Topics"]:
                                topic_title = topic["Title"]
                                if topic_title in weighted_topics[subject]:
                                    module_topics[topic_title] = weighted_topics[subject][topic_title]
                            
                            if module_topics:
                                # Use weighted selection
                                topics = list(module_topics.keys())
                                weights = list(module_topics.values())
                                selected_title = random.choices(topics, weights=weights, k=1)[0]
                                topic = next((t for t in module["Topics"] if t["Title"] == selected_title), None)
                                if not topic:  # Fallback if topic not found
                                    topic = random.choice(module["Topics"])
                            else:
                                # No weights available for this module's topics
                                topic = random.choice(module["Topics"])
                        else:
                            # No weights available for this subject
                            topic = random.choice(module["Topics"])
                            
                        # Force Uplearn task type if this is an uplearn subject
                        if is_uplearn_task:
                            task = {
                                "subject": f"{subject} ({year['Name']})",
                                "task": f"Complete Uplearn session on {topic['Title']}",
                                "duration": subject_minutes // 2,
                                "type": "Uplearn"
                            }
                        else:
                            task = generate_task_for_topic(f"{subject} ({year['Name']})", 
                                                        topic, 
                                                        subject_minutes // 2)
                        tasks.append(task)
        else:
            # Handle other subjects
            if "Papers" in subject_data:  # Psychology
                paper = random.choice(subject_data["Papers"])
                
                # Select topic with weighting if available for Psychology
                if subject in weighted_topics and weighted_topics[subject]:
                    # Find topics from this paper that have proficiency ratings
                    paper_topics = {}
                    for topic in paper["Topics"]:
                        topic_title = topic["Title"]
                        if topic_title in weighted_topics[subject]:
                            paper_topics[topic_title] = weighted_topics[subject][topic_title]
                    
                    if paper_topics:
                        # Use weighted selection
                        topics = list(paper_topics.keys())
                        weights = list(paper_topics.values())
                        selected_title = random.choices(topics, weights=weights, k=1)[0]
                        topic = next((t for t in paper["Topics"] if t["Title"] == selected_title), None)
                        if not topic:  # Fallback if topic not found
                            topic = random.choice(paper["Topics"])
                    else:
                        # No weights available for this paper's topics
                        topic = random.choice(paper["Topics"])
                else:
                    # No weights available for Psychology
                    topic = random.choice(paper["Topics"])
                
                task = generate_task_for_topic(subject, topic, subject_minutes)
                tasks.append(task)
                
            elif "Modules" in subject_data:  # Chemistry
                module = random.choice(subject_data["Modules"])
                if module["Topics"]:
                    # Select topic with weighting if available for Chemistry
                    if subject in weighted_topics and weighted_topics[subject]:
                        # Find topics from this module that have proficiency ratings
                        module_topics = {}
                        for topic in module["Topics"]:
                            topic_title = topic["Title"]
                            if topic_title in weighted_topics[subject]:
                                module_topics[topic_title] = weighted_topics[subject][topic_title]
                        
                        if module_topics:
                            # Use weighted selection
                            topics = list(module_topics.keys())
                            weights = list(module_topics.values())
                            selected_title = random.choices(topics, weights=weights, k=1)[0]
                            topic = next((t for t in module["Topics"] if t["Title"] == selected_title), None)
                            if not topic:  # Fallback if topic not found
                                topic = random.choice(module["Topics"])
                        else:
                            # No weights available for this module's topics
                            topic = random.choice(module["Topics"])
                    else:
                        # No weights available for Chemistry
                        topic = random.choice(module["Topics"])
                    
                    # Force Uplearn task type if this is an uplearn subject
                    if is_uplearn_task:
                        task = {
                            "subject": subject,
                            "task": f"Complete Uplearn session on {topic['Title']}",
                            "duration": subject_minutes,
                            "type": "Uplearn"
                        }
                    else:
                        task = generate_task_for_topic(subject, topic, subject_minutes)
                    tasks.append(task)
    
    return tasks

def get_uplearn_link(subject):
    """Get the UpLearn link for a subject"""
    links = {
        "Chemistry": "https://web.uplearn.co.uk/learn/chemistry-ocr-2",
        "Biology (Year 13)": "https://web.uplearn.co.uk/learn/biology-ocr-2",
        "Biology (Y13)": "https://web.uplearn.co.uk/learn/biology-ocr-2",
        "Biology (Year 12)": "https://web.uplearn.co.uk/learn/biology-ocr-1",
        "Biology (Y12)": "https://web.uplearn.co.uk/learn/biology-ocr-1",
        "Biology": "https://web.uplearn.co.uk/learn/biology-ocr-2"
    }
    return links.get(subject, "")

# Sample Data for Timetable & Weekend Tasks
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

# Add subject end dates for 2025 A-levels with multiple exam dates
SUBJECT_END_DATES = {
    'Psychology': [
        {'paper': 'Paper 1', 'date': '2025-06-09', 'topics': 'Social Influence, Memory, Attachment, Psychopathology'},
        {'paper': 'Paper 2', 'date': '2025-06-18', 'topics': 'Approaches, Biopsychology, Research Methods'},
        {'paper': 'Paper 3', 'date': '2025-06-26', 'topics': 'Issues & Debates, Schizophrenia, Aggression, Relationships'}
    ],
    'Chemistry': [
        {'paper': 'Paper 1', 'date': '2025-06-16', 'topics': 'Inorganic & Physical Chemistry'},
        {'paper': 'Paper 2', 'date': '2025-06-24', 'topics': 'Organic & Physical Chemistry'},
        {'paper': 'Paper 3', 'date': '2025-07-02', 'topics': 'Practical Skills & All Content'}
    ],
    'Biology': [
        {'paper': 'Paper 1', 'date': '2025-06-19', 'topics': 'Biological Processes'},
        {'paper': 'Paper 2', 'date': '2025-06-27', 'topics': 'Biological Diversity'},
        {'paper': 'Paper 3', 'date': '2025-07-03', 'topics': 'Unified Biology'}
    ]
}

def get_calendar_data(start_date=None):
    """Generate calendar data with exam dates"""
    if not start_date:
        start_date = datetime.now()
    
    weeks = []
    current_date = start_date
    
    # Calculate exam dates and create a map of important dates
    important_dates = {}
    for subject, exams in SUBJECT_END_DATES.items():
        for exam in exams:
            exam_date = exam['date']
            important_dates[exam_date] = important_dates.get(exam_date, []) + [
                {'subject': subject, 'exam': exam['paper'], 'topics': exam['topics']}
            ]
    
    for week in range(1, 16):  # Generate 15 weeks of data
        week_data = {
            'week_number': week,
            'start_date': current_date.strftime('%Y-%m-%d'),
            'end_date': (current_date + timedelta(days=6)).strftime('%Y-%m-%d'),
            'subjects': {},
            'days': [],
            'exams': []
        }
        
        # Generate daily data for each day of the week
        for day_offset in range(7):
            day_date = current_date + timedelta(days=day_offset)
            day_str = day_date.strftime('%Y-%m-%d')
            day_name = day_date.strftime('%A')
            
            # Check if this day has any exams
            day_exams = important_dates.get(day_str, [])
            
            day_data = {
                'date': day_str,
                'day_name': day_name,
                'tasks': weekday_timetable.get(day_name, []),
                'exams': day_exams
            }
            
            # Add exams to the week's exam list
            week_data['exams'].extend(day_exams)
            
            week_data['days'].append(day_data)
        
        # Add subject data with next exam information
        for subject, exams in SUBJECT_END_DATES.items():
            # Find the next exam for this subject from the current date
            next_exam = None
            for exam in exams:
                exam_date = datetime.strptime(exam['date'], '%Y-%m-%d')
                if exam_date >= current_date:
                    if next_exam is None or exam_date < datetime.strptime(next_exam['date'], '%Y-%m-%d'):
                        next_exam = exam
            
            if next_exam:
                week_data['subjects'][subject] = {
                    'tasks': weekday_timetable.get(current_date.strftime('%A'), []),
                    'end_date': next_exam['date'],
                    'next_exam': next_exam
                }
        
        weeks.append(week_data)
        current_date += timedelta(days=7)
    
    return weeks

def filter_timetable_for_user(timetable, user):
    """Filter timetable tasks based on user's selected subjects"""
    filtered_timetable = {}
    for day, day_tasks in timetable.items():
        filtered_day_tasks = []
        for task in day_tasks:
            task_subject = task.split(":")[0]
            if "Chemistry" in task_subject and (not user.subjects or user.subjects.chemistry):
                filtered_day_tasks.append(task)
            elif "Biology" in task_subject and (not user.subjects or user.subjects.biology):
                filtered_day_tasks.append(task)
            elif "Psychology" in task_subject:
                filtered_day_tasks.append(task)
        
        if filtered_day_tasks:
            filtered_timetable[day] = filtered_day_tasks
    
    return filtered_timetable

# -------------------------
# Routes
# -------------------------
@app.route("/")
def home():
    if current_user.is_authenticated:
        try:
            if current_user.onboarding_step < 2:
                return redirect(url_for("welcome"))
        except AttributeError:
            return redirect(url_for("welcome"))
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for("register"))
        
        # Create user
        new_user = User(
            username=username,
            password=generate_password_hash(password, method="pbkdf2:sha256"),
            onboarding_step=0,
            daily_study_hours=4.0
        )
        
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.")
        return redirect(url_for("login"))
    return render_template("register.html")

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

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST" and "update_progress" in request.form:
        try:
            new_chem = int(request.form.get("chem_progress", 0))
            new_bio_y13 = int(request.form.get("bio_y13_progress", 0))
            new_bio_y12 = int(request.form.get("bio_y12_progress", 0))
            
            if any([
                new_chem != current_user.chem_progress,
                new_bio_y13 != current_user.bio_y13_progress,
                new_bio_y12 != current_user.bio_y12_progress
            ]):
                current_user.chem_progress = new_chem
                current_user.bio_y13_progress = new_bio_y13
                current_user.bio_y12_progress = new_bio_y12
                db.session.commit()
                flash("Progress updated successfully!")
        except ValueError:
            flash("Error updating progress. Please check your inputs.")
        return redirect(url_for('dashboard'))
    
    curriculum_data = load_curriculum()
    
    # Get user's selected subjects for task filtering
    user_subjects = []
    uplearn_subjects = []
    if current_user.subjects:
        if current_user.subjects.biology:
            user_subjects.append("Biology")
            uplearn_subjects.append("Biology")
        if current_user.subjects.chemistry:
            user_subjects.append("Chemistry")
            uplearn_subjects.append("Chemistry")
    # Always include Psychology
    if "Psychology" in curriculum_data:
        user_subjects.append("Psychology")
    
    # Get user's topic proficiencies for personalized task generation
    user_proficiencies = {}
    try:
        # Check if the topic_proficiency table exists
        topic_proficiencies = TopicProficiency.query.filter_by(user_id=current_user.id).all()
        
        for proficiency in topic_proficiencies:
            if proficiency.subject not in user_proficiencies:
                user_proficiencies[proficiency.subject] = {}
            user_proficiencies[proficiency.subject][proficiency.topic] = proficiency.proficiency
    except Exception as e:
        # If table doesn't exist yet, proceed without proficiencies
        print(f"Note: Unable to load topic proficiencies: {e}")
    
    # Generate tasks based on user's selected subjects, uplearn preferences, and topic proficiencies
    daily_tasks = generate_daily_tasks(curriculum_data, user_subjects, uplearn_subjects, user_proficiencies)
    
    # Filter timetable for user's subjects
    filtered_timetable = filter_timetable_for_user(weekday_timetable, current_user)
    
    # Get calendar data for compact view
    calendar_data = get_calendar_data()
    
    # Get the next upcoming exam for each subject
    upcoming_exams = {}
    for subject, exams in SUBJECT_END_DATES.items():
        next_exams = sorted([exam for exam in exams if days_until_filter(exam['date']) > 0], 
                          key=lambda x: days_until_filter(x['date']))
        if next_exams:
            upcoming_exams[subject] = next_exams[0]
    
    return render_template(
        "dashboard.html",
        user=current_user,
        daily_tasks=daily_tasks,
        get_uplearn_link=get_uplearn_link,
        timetable=filtered_timetable,
        subject_end_dates=SUBJECT_END_DATES,
        upcoming_exams=upcoming_exams,
        calendar_data=calendar_data,
        now=datetime.now()
    )

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

@app.route("/study_planner")
@login_required
def study_planner():
    calendar_data = get_calendar_data()
    
    # Get user's selected subjects for task filtering
    user_subjects = []
    uplearn_subjects = []
    if current_user.subjects:
        if current_user.subjects.biology:
            user_subjects.append("Biology")
            uplearn_subjects.append("Biology")
        if current_user.subjects.chemistry:
            user_subjects.append("Chemistry")
            uplearn_subjects.append("Chemistry")
    # Always include Psychology
    if "Psychology" in load_curriculum():
        user_subjects.append("Psychology")
        
    # Filter weekend tasks based on user's selected subjects
    filtered_weekend_tasks = []
    for task in weekend_tasks:
        task_subject = task["task"].split(":")[0]
        if "Biology" in task_subject and "Biology" in user_subjects:
            filtered_weekend_tasks.append(task)
        elif "Chemistry" in task_subject and "Chemistry" in user_subjects:
            filtered_weekend_tasks.append(task)
        elif "Psychology" in task_subject:
            filtered_weekend_tasks.append(task)
    
    # Filter timetable for user's subjects
    filtered_timetable = filter_timetable_for_user(weekday_timetable, current_user)
    
    # Get the next upcoming exam for each subject
    upcoming_exams = {}
    for subject, exams in SUBJECT_END_DATES.items():
        next_exams = sorted([exam for exam in exams if days_until_filter(exam['date']) > 0], 
                          key=lambda x: days_until_filter(x['date']))
        if next_exams:
            upcoming_exams[subject] = next_exams[0]
    
    return render_template(
        "study_planner.html",
        user=current_user,
        timetable=filtered_timetable,
        tasks=filtered_weekend_tasks,
        calendar_data=calendar_data,
        subject_end_dates=SUBJECT_END_DATES,
        upcoming_exams=upcoming_exams,
        now=datetime.now()
    )

@app.route("/curriculum")
@login_required
def curriculum():
    curriculum_data = load_curriculum()
    
    # Get user's proficiency ratings
    proficiencies = {}
    try:
        user_ratings = TopicProficiency.query.filter_by(user_id=current_user.id).all()
        
        for rating in user_ratings:
            if rating.subject not in proficiencies:
                proficiencies[rating.subject] = {}
            proficiencies[rating.subject][rating.topic] = rating.proficiency
    except Exception as e:
        # If table doesn't exist yet, proceed without proficiencies
        print(f"Note: Unable to load topic proficiencies: {e}")
    
    return render_template(
        "curriculum.html",
        curriculum=curriculum_data,
        proficiencies=proficiencies
    )

@app.route("/welcome", methods=["GET", "POST"])
@login_required
def welcome():
    curriculum_data = load_curriculum()
    
    # Handle case where onboarding_step attribute doesn't exist yet
    try:
        onboarding_step = current_user.onboarding_step
    except AttributeError:
        current_user.onboarding_step = 0
        db.session.commit()
        onboarding_step = 0
        
    settings_mode = onboarding_step >= 2
    
    if request.method == "POST":
        print(f"Form data received: {request.form}")
        
        if "step1" in request.form:
            print("Processing step 1")
            # Process subject selection and study preferences
            if not current_user.subjects:
                subjects = UserSubjects(user_id=current_user.id)
                db.session.add(subjects)
            else:
                subjects = current_user.subjects
            
            subjects.chemistry = request.form.get("chemistry") == "on"
            subjects.biology = request.form.get("biology") == "on"
            
            # Update daily study hours
            try:
                current_user.daily_study_hours = float(request.form.get("daily_study_hours", 4.0))
            except (ValueError, AttributeError):
                current_user.daily_study_hours = 4.0
            
            # Update onboarding step
            if current_user.onboarding_step < 1:
                current_user.onboarding_step = 1
            
            db.session.commit()
            print(f"User updated: onboarding_step={current_user.onboarding_step}")
            
            # For settings mode, redirect back to dashboard after save
            if settings_mode:
                flash("Settings updated successfully!")
                return redirect(url_for("dashboard"))
            
            # Otherwise continue to step 2
            flash("Subject preferences saved! Continue to set up your topic preferences.")
            return redirect(url_for("welcome"))
            
        elif "step2" in request.form:
            print("Processing step 2")
            # Process curriculum preferences
            current_user.onboarding_step = 2
            db.session.commit()
            print(f"User updated: onboarding_step={current_user.onboarding_step}")
            
            if settings_mode:
                flash("Settings updated successfully!")
                return redirect(url_for("dashboard"))
            else:
                flash("Setup complete! Welcome to your personalized study planner.")
                return redirect(url_for("dashboard"))
    
    # Make sure curriculum data is available
    if not curriculum_data:
        curriculum_data = {
            "Psychology": ["Memory", "Attachment", "Social Influence", "Psychopathology"],
            "Chemistry": ["Atomic Structure", "Bonding", "Energetics", "Kinetics", "Equilibria"],
            "Biology": ["Cell Biology", "Biological Molecules", "Genetics", "Ecology"]
        }
    
    return render_template(
        "welcome.html",
        user=current_user,
        curriculum=curriculum_data,
        settings_mode=settings_mode,
        fullscreen_mode=True
    )

@app.route("/study_analytics")
@login_required
def study_analytics():
    # Get task logs for the current user, ordered by most recent
    task_logs = TaskLog.query.filter_by(user_id=current_user.id).order_by(TaskLog.date_completed.desc()).all()
    
    # Get UpLearn logs for the current user
    uplearn_logs = UplearnLog.query.filter_by(user_id=current_user.id).order_by(UplearnLog.date.desc()).all()
    
    # Calculate completion statistics by week
    week_stats = {}
    today = datetime.now().date()
    
    # Process the last 12 weeks of data
    for i in range(12):
        week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        week_label = f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}"
        
        # Count tasks completed this week by subject
        week_tasks = [log for log in task_logs 
                     if week_start <= log.date_completed.date() <= week_end]
        
        # Group by subject
        subjects = {}
        for log in week_tasks:
            subjects[log.subject] = subjects.get(log.subject, 0) + 1
        
        # Calculate time spent in hours
        total_time = sum(log.duration for log in week_tasks) / 60.0 if week_tasks else 0
        
        # Get uplearn progress this week
        week_uplearn = [log for log in uplearn_logs 
                       if week_start <= log.date <= week_end]
        uplearn_lessons = sum(log.lessons_completed for log in week_uplearn)
        
        week_stats[week_label] = {
            'tasks': len(week_tasks),
            'subjects': subjects,
            'time_spent': round(total_time, 1),
            'uplearn_lessons': uplearn_lessons
        }
    
    # Calculate efficiency and productivity metrics
    if task_logs:
        avg_duration_by_subject = {}
        avg_difficulty_by_subject = {}
        
        for subject in ['Chemistry', 'Biology Y13', 'Biology Y12', 'Psychology']:
            subject_logs = [log for log in task_logs if log.subject == subject]
            if subject_logs:
                avg_duration_by_subject[subject] = sum(log.duration for log in subject_logs) / len(subject_logs)
                avg_difficulty_by_subject[subject] = sum(log.difficulty for log in subject_logs) / len(subject_logs)
        
        # Calculate productivity score (tasks completed per hour of study)
        total_hours = sum(log.duration for log in task_logs) / 60.0
        productivity = len(task_logs) / total_hours if total_hours > 0 else 0
    else:
        avg_duration_by_subject = {}
        avg_difficulty_by_subject = {}
        productivity = 0
    
    # Analyze time distribution
    time_distribution = {
        'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 'Thursday': 0,
        'Friday': 0, 'Saturday': 0, 'Sunday': 0
    }
    
    # Track productivity by day of week
    day_productivity = {
        'Monday': {'time': 0, 'tasks': 0}, 'Tuesday': {'time': 0, 'tasks': 0},
        'Wednesday': {'time': 0, 'tasks': 0}, 'Thursday': {'time': 0, 'tasks': 0},
        'Friday': {'time': 0, 'tasks': 0}, 'Saturday': {'time': 0, 'tasks': 0},
        'Sunday': {'time': 0, 'tasks': 0}
    }
    
    # Analyze time spent on each task
    for log in task_logs:
        day_name = log.date_completed.strftime('%A')
        time_distribution[day_name] += log.duration
        day_productivity[day_name]['time'] += log.duration
        day_productivity[day_name]['tasks'] += 1
    
    # Add UpLearn time
    for log in uplearn_logs:
        day_name = log.date.strftime('%A')
        time_distribution[day_name] += log.time_spent
    
    # Calculate productivity (tasks per hour)
    productivity_by_day = {}
    for day, data in day_productivity.items():
        if data['time'] > 0:
            hours = data['time'] / 60.0
            productivity_by_day[day] = data['tasks'] / hours
        else:
            productivity_by_day[day] = 0
    
    # Streak analysis
    if task_logs:
        # Check if there's a log from today
        current_date = datetime.now().date()
        today_log = any(log.date_completed.date() == current_date for log in task_logs)
        
        current_streak = 1 if today_log else 0
        if not today_log:
            # Check yesterday
            yesterday = current_date - timedelta(days=1)
            if any(log.date_completed.date() == yesterday for log in task_logs):
                current_streak = 1
        
        # Calculate max streak
        streak_dates = set(log.date_completed.date() for log in task_logs)
        date_ranges = sorted(streak_dates)
        
        max_streak = 1
        if date_ranges:
            for i in range(1, len(date_ranges)):
                date_diff = (date_ranges[i] - date_ranges[i-1]).days
                if date_diff > 1:  # Streak broken
                    # Calculate max streak
                    streak_length = i
                    if streak_length > max_streak:
                        max_streak = streak_length
    else:
        current_streak = 0
        max_streak = 0
    
    return render_template(
        "study_analytics.html",
        task_logs=task_logs,
        uplearn_logs=uplearn_logs,
        week_stats=week_stats,
        avg_duration_by_subject=avg_duration_by_subject,
        avg_difficulty_by_subject=avg_difficulty_by_subject,
        productivity=productivity,
        time_distribution=time_distribution,
        productivity_by_day=productivity_by_day,
        day_productivity=day_productivity,
        current_streak=current_streak,
        max_streak=max_streak,
        now=datetime.now()
    )

@app.route("/time_analysis")
@login_required
def time_analysis():
    # Get task logs for the current user
    task_logs = TaskLog.query.filter_by(user_id=current_user.id).all()
    
    # Get UpLearn logs for the current user
    uplearn_logs = UplearnLog.query.filter_by(user_id=current_user.id).all()
    
    # Analyze time distribution
    time_distribution = {
        'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 'Thursday': 0,
        'Friday': 0, 'Saturday': 0, 'Sunday': 0
    }
    
    # Track productivity by day of week
    day_productivity = {
        'Monday': {'time': 0, 'tasks': 0}, 'Tuesday': {'time': 0, 'tasks': 0},
        'Wednesday': {'time': 0, 'tasks': 0}, 'Thursday': {'time': 0, 'tasks': 0},
        'Friday': {'time': 0, 'tasks': 0}, 'Saturday': {'time': 0, 'tasks': 0},
        'Sunday': {'time': 0, 'tasks': 0}
    }
    
    # Analyze time spent on each task
    for log in task_logs:
        day_name = log.date_completed.strftime('%A')
        time_distribution[day_name] += log.duration
        day_productivity[day_name]['time'] += log.duration
        day_productivity[day_name]['tasks'] += 1
    
    # Add UpLearn time
    for log in uplearn_logs:
        day_name = log.date.strftime('%A')
        time_distribution[day_name] += log.time_spent
    
    # Calculate productivity (tasks per hour)
    productivity_by_day = {}
    for day, data in day_productivity.items():
        if data['time'] > 0:
            hours = data['time'] / 60.0
            productivity_by_day[day] = data['tasks'] / hours
        else:
            productivity_by_day[day] = 0
    
    # Streak analysis
    if task_logs:
        # Check if there's a log from today
        current_date = datetime.now().date()
        today_log = any(log.date_completed.date() == current_date for log in task_logs)
        
        current_streak = 1 if today_log else 0
        if not today_log:
            # Check yesterday
            yesterday = current_date - timedelta(days=1)
            if any(log.date_completed.date() == yesterday for log in task_logs):
                current_streak = 1
        
        # Calculate max streak
        streak_dates = set(log.date_completed.date() for log in task_logs)
        date_ranges = sorted(streak_dates)
        
        max_streak = 1
        if date_ranges:
            for i in range(1, len(date_ranges)):
                date_diff = (date_ranges[i] - date_ranges[i-1]).days
                if date_diff > 1:  # Streak broken
                    # Calculate max streak
                    streak_length = i
                    if streak_length > max_streak:
                        max_streak = streak_length
    else:
        current_streak = 0
        max_streak = 0
    
    return render_template(
        "time_analysis.html",
        time_distribution=time_distribution,
        productivity_by_day=productivity_by_day,
        current_streak=current_streak,
        max_streak=max_streak
    )

@app.route("/progress_log", methods=["GET", "POST"])
@login_required
def progress_log():
    # Check for prefilled task info from dashboard
    prefilled_task = {
        'task': request.args.get('task', ''),
        'subject': request.args.get('subject', ''),
        'duration': request.args.get('duration', '')
    }
    
    if request.method == "POST":
        if "log_task" in request.form:
            # Log a completed task
            new_task = TaskLog(
                user_id=current_user.id,
                task=request.form.get("task"),
                subject=request.form.get("subject"),
                duration=request.form.get("duration"),
                difficulty=request.form.get("difficulty"),
                notes=request.form.get("notes")
            )
            db.session.add(new_task)
            db.session.commit()
            flash("Task logged successfully!")
            
        elif "log_uplearn" in request.form:
            # Log UpLearn progress
            new_uplearn = UplearnLog(
                user_id=current_user.id,
                subject=request.form.get("subject"),
                lessons_completed=request.form.get("lessons_completed"),
                time_spent=request.form.get("time_spent"),
                comprehension=request.form.get("comprehension")
            )
            db.session.add(new_uplearn)
            db.session.commit()
            flash("UpLearn progress logged successfully!")
            
        return redirect(url_for("progress_log"))
    
    # Get task logs for the current user, ordered by most recent
    task_logs = TaskLog.query.filter_by(user_id=current_user.id).order_by(TaskLog.date_completed.desc()).all()
    
    # Get UpLearn logs for the current user
    uplearn_logs = UplearnLog.query.filter_by(user_id=current_user.id).order_by(UplearnLog.date.desc()).all()
    
    # Calculate UpLearn statistics
    uplearn_stats = {
        "Chemistry": {"daily": [], "weekly": []},
        "Biology Y12": {"daily": [], "weekly": []},
        "Biology Y13": {"daily": [], "weekly": []}
    }
    
    # Process daily stats
    for subject in uplearn_stats:
        # Get last 14 days of data
        today = datetime.now().date()
        for i in range(14):
            day = today - timedelta(days=i)
            logs = [log for log in uplearn_logs if log.subject == subject and log.date == day]
            
            # Calculate daily stats
            daily_lessons = sum(log.lessons_completed for log in logs)
            uplearn_stats[subject]["daily"].append({
                "date": day.strftime("%Y-%m-%d"),
                "lessons": daily_lessons
            })
        
        # Weekly stats (last 8 weeks)
        for i in range(8):
            week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            
            logs = [log for log in uplearn_logs 
                if log.subject == subject 
                and week_start <= log.date <= week_end]
            
            weekly_lessons = sum(log.lessons_completed for log in logs)
            uplearn_stats[subject]["weekly"].append({
                "week": f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}",
                "lessons": weekly_lessons
            })
    
    return render_template(
        "progress_log.html",
        task_logs=task_logs,
        uplearn_logs=uplearn_logs,
        uplearn_stats=uplearn_stats,
        prefilled_task=prefilled_task,
        show_task_modal=bool(prefilled_task['task']),
        user=current_user
    )

@app.route("/complete_task", methods=["POST"])
@login_required
def complete_task():
    """Endpoint for quickly marking tasks as complete"""
    task = request.form.get("task")
    subject = request.form.get("subject")
    duration = request.form.get("duration", 30)  # Default 30 minutes
    difficulty = request.form.get("difficulty", 3)  # Default medium difficulty
    
    if not task or not subject:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": "Missing task information"}), 400
        flash("Missing task information.")
        return redirect(url_for("dashboard"))
    
    # Create new task log
    new_task = TaskLog(
        user_id=current_user.id,
        task=task,
        subject=subject,
        duration=duration,
        difficulty=difficulty,
        notes="Completed via quick action"
    )
    db.session.add(new_task)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "message": f"Task '{task}' marked as complete."})
    
    flash(f"Task '{task}' marked as complete!")
    return redirect(url_for("dashboard"))

def init_db():
    """Initialize the database and ensure schema is up to date"""
    with app.app_context():
        # Attempt to create all tables including the new TopicProficiency table
        db.create_all()
        
        # Verify the table exists 
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'topic_proficiency' not in inspector.get_table_names():
                # Force create the TopicProficiency table specifically
                TopicProficiency.__table__.create(db.engine, checkfirst=True)
            print("Database schema successfully updated!")
        except Exception as e:
            print(f"Warning: Could not verify table creation: {e}")
            # Still try to create the table directly
            try:
                TopicProficiency.__table__.create(db.engine, checkfirst=True)
                print("TopicProficiency table created successfully!")
            except Exception as inner_e:
                print(f"Error creating TopicProficiency table: {inner_e}")
                
        print("Database initialization complete!")

@app.route("/api/ratings/save", methods=['POST'])
@login_required
def save_rating():
    """API endpoint to save topic proficiency ratings"""
    data = request.json
    topic_id = data.get('topic_id')  # This will be the topic name
    rating = data.get('rating')
    
    if not topic_id or not rating:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Convert topic_id to actual topic name (remove underscores, etc.)
    topic_name = topic_id.replace('_', ' ')
    
    # Determine the subject based on the topic name
    curriculum = load_curriculum().get('Curriculum', {})
    subject = None
    for subj, topics in curriculum.items():
        if topic_name in topics:
            subject = subj
            break
    
    if not subject:
        # Fallback: check if the topic_id contains the subject name
        if 'biology' in topic_id.lower():
            subject = 'Biology'
        elif 'chemistry' in topic_id.lower():
            subject = 'Chemistry'
        elif 'psychology' in topic_id.lower():
            subject = 'Psychology'
        else:
            return jsonify({'error': 'Could not determine subject for topic'}), 400
    
    try:
        # Ensure the TopicProficiency table exists
        init_db()
        
        # Check if a rating exists already
        rating_obj = TopicProficiency.query.filter_by(
            user_id=current_user.id, 
            subject=subject,
            topic=topic_name
        ).first()
        
        if rating_obj:
            # Update existing rating
            rating_obj.proficiency = rating
        else:
            # Create new rating
            rating_obj = TopicProficiency(
                user_id=current_user.id,
                subject=subject,
                topic=topic_name,
                proficiency=rating
            )
            db.session.add(rating_obj)
            
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route("/api/ratings/get", methods=['GET'])
@login_required
def get_ratings():
    """API endpoint to get user's topic proficiency ratings"""
    try:
        # Ensure the TopicProficiency table exists
        init_db()
        
        # Get all ratings for current user
        ratings = TopicProficiency.query.filter_by(user_id=current_user.id).all()
        
        # Create a dictionary mapping topics to their proficiency levels
        ratings_dict = {}
        for r in ratings:
            topic_id = r.topic.lower().replace(' ', '_')
            ratings_dict[topic_id] = r.proficiency
        
        return jsonify({
            'success': True,
            'ratings': ratings_dict
        })
    except Exception as e:
        # Return empty ratings if there's an error
        return jsonify({
            'success': True,
            'ratings': {},
            'note': f"Could not retrieve ratings: {str(e)}"
        })

# Run the application
if __name__ == "__main__":
    # Create database and update schema
    init_db()
    app.run(debug=True)