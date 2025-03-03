import sys
import subprocess
import os
import platform
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy.pool import NullPool
import json

def verify_dependencies():
    """Verify all required packages are installed"""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if not os.path.exists(requirements_path):
        print("Error: requirements.txt not found!")
        sys.exit(1)

    # Read requirements file
    with open(requirements_path) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Check Python version for SQLAlchemy compatibility
    python_version = tuple(map(int, platform.python_version_tuple()))
    upgrade_packages = []
    
    # Python 3.13 compatibility fixes
    if python_version >= (3, 13):
        print(f"Detected Python {'.'.join(map(str, python_version))}...")
        # SQLAlchemy 2.0.x has issues with Python 3.13
        for i, req in enumerate(requirements):
            if req.lower().startswith('sqlalchemy==2.0.'):
                print("Detected potentially incompatible SQLAlchemy version for Python 3.13")
                requirements[i] = 'sqlalchemy>=2.0.27'
                upgrade_packages.append('sqlalchemy>=2.0.27')
                
            # Check if Flask-SQLAlchemy might need upgrade too
            if req.lower().startswith('flask-sqlalchemy==') and not req.endswith('3.1.1'):
                requirements[i] = 'flask-sqlalchemy>=3.1.1'
                upgrade_packages.append('flask-sqlalchemy>=3.1.1')
    
    try:
        # Try to use importlib_metadata to check installed packages
        try:
            from importlib.metadata import version, PackageNotFoundError
            
            missing = []
            for req in requirements:
                pkg_name = req.split('==')[0].split('>=')[0].strip()
                try:
                    version(pkg_name)
                except PackageNotFoundError:
                    missing.append(pkg_name)
        except ImportError:
            # Fall back to pkg_resources
            print("Using pkg_resources for package verification...")
            try:
                import pkg_resources
            except ImportError:
                print("Installing setuptools package...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'setuptools'])
                import pkg_resources
            
            # Check installed packages
            installed = {pkg.key for pkg in pkg_resources.working_set}
            missing = [pkg.split('==')[0].split('>=')[0].strip() for pkg in requirements if pkg.split('==')[0].split('>=')[0].strip().lower() not in installed]
    except Exception as e:
        # Fallback method - just try to import each package
        print(f"Using fallback method to check packages: {e}")
        missing = []
        for pkg in requirements:
            try:
                pkg_name = pkg.split('==')[0].split('>=')[0].strip()
                __import__(pkg_name)
            except ImportError:
                missing.append(pkg_name)
    
    # Handle upgrades for Python 3.13 compatibility
    if upgrade_packages and python_version >= (3, 13):
        print("Upgrading packages for Python 3.13 compatibility...")
        try:
            for pkg in upgrade_packages:
                print(f"Upgrading {pkg}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-U', pkg])
            print("Package upgrades completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to upgrade some packages: {e}")
    
    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        print("Installing...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_path])
            print("All required packages installed successfully!")
        except subprocess.CalledProcessError:
            print("Error: Failed to install required packages!")
            sys.exit(1)
    
    return True

# Make sure all dependencies are installed
verify_dependencies()

# Initialize Flask app and configure it
app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key_here"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"poolclass": NullPool}

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Constants
SUBJECT_END_DATES = {
    'Chemistry': [
        {'date': '2025-06-10', 'paper': 'Paper 1 (Physical Chemistry)', 'duration': '2h 15m'},
        {'date': '2025-06-17', 'paper': 'Paper 2 (Organic Chemistry)', 'duration': '2h 15m'},
        {'date': '2025-06-24', 'paper': 'Paper 3 (Advanced Chemistry)', 'duration': '1h 30m'}
    ],
    'Biology': [
        {'date': '2025-05-20', 'paper': 'Paper 1 (AS Content)', 'duration': '2h'},
        {'date': '2025-06-03', 'paper': 'Paper 2 (A2 Content)', 'duration': '2h'},
        {'date': '2025-06-12', 'paper': 'Paper 3 (Practical Skills)', 'duration': '1h 30m'}
    ],
    'Psychology': [
        {'date': '2025-05-15', 'paper': 'Paper 1 (Core Content)', 'duration': '2h'},
        {'date': '2025-05-28', 'paper': 'Paper 2 (Research Methods)', 'duration': '2h'},
        {'date': '2025-06-07', 'paper': 'Paper 3 (Options)', 'duration': '2h'}
    ]
}

# Sample weekend tasks with point values
weekend_tasks = [
    {"task": "Chemistry: Complete Past Paper", "points": 50},
    {"task": "Biology: Essay Practice", "points": 40},
    {"task": "Psychology: Research Methods Practice", "points": 45},
    {"task": "Chemistry: Reaction Mechanisms Review", "points": 35},
    {"task": "Biology: Exam Style Questions", "points": 40},
    {"task": "Psychology: Model Essays", "points": 45},
]

# Sample weekday timetable structure
weekday_timetable = {
    "Monday": [
        "Chemistry: Physical Chemistry",
        "Biology: Cell Biology",
        "Psychology: Research Methods"
    ],
    "Tuesday": [
        "Chemistry: Organic Chemistry",
        "Biology: Genetics",
        "Psychology: Memory"
    ],
    "Wednesday": [
        "Chemistry: Inorganic Chemistry",
        "Biology: Evolution",
        "Psychology: Social Influence"
    ],
    "Thursday": [
        "Chemistry: Analytical Chemistry",
        "Biology: Homeostasis",
        "Psychology: Attachment"
    ],
    "Friday": [
        "Chemistry: Practical Skills",
        "Biology: Ecology",
        "Psychology: Psychopathology"
    ]
}

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

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    chem_progress = db.Column(db.Integer, default=0)
    bio_y13_progress = db.Column(db.Integer, default=0)
    bio_y12_progress = db.Column(db.Integer, default=0)
    welcome_completed = db.Column(db.Boolean, default=False)
    daily_study_hours = db.Column(db.Float, default=4.0)
    onboarding_step = db.Column(db.Integer, default=1)  # Track which step of welcome they're on
    last_welcome_shown = db.Column(db.DateTime)  # Track when welcome was last shown
    subjects = db.relationship('UserSubjects', backref='user', uselist=False)
    task_logs = db.relationship('TaskLog', backref='user', lazy=True)
    uplearn_logs = db.relationship('UplearnLog', backref='user', lazy=True)
    topic_preferences = db.relationship('TopicPreference', backref='user', lazy=True)

class TopicPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    frequency = db.Column(db.Integer, default=0)  # -1 for less frequent, 0 for default, 1 for more frequent
    last_modified = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    __table_args__ = (db.UniqueConstraint('user_id', 'subject', 'topic', name='unique_topic_pref'),)

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

@login_manager.user_loader
def load_user(user_id):
    # Update to use newer SQLAlchemy syntax
    return db.session.get(User, int(user_id))

# ---------------------------
# Routes
# ---------------------------
@app.before_request
def check_welcome_status():
    """Check if user needs to complete welcome process"""
    if current_user.is_authenticated and not current_user.welcome_completed:
        # Only redirect to welcome if not already there and not accessing static resources or logging out
        if request.endpoint not in ['welcome', 'static', 'logout']:
            return redirect(url_for('welcome'))

# Rest of the app code remains the same...

# Welcome route
@app.route("/welcome", methods=["GET", "POST"])
@login_required
def welcome():
    """Welcome page with subject selection and curriculum preferences"""
    settings_mode = request.args.get('settings') == 'true'
    curriculum_data = load_curriculum()
    
    if request.method == "POST":
        # Handle step 1 submission (subject selection)
        if "step1" in request.form:
            # Update subject preferences
            if not current_user.subjects:
                subjects = UserSubjects(user_id=current_user.id)
                db.session.add(subjects)
            else:
                subjects = current_user.subjects
            
            subjects.chemistry = request.form.get("chemistry") == "on"
            subjects.biology = request.form.get("biology") == "on"
            
            # Update study preferences - only daily study hours
            current_user.daily_study_hours = float(request.form.get("daily_study_hours", 4.0))
            current_user.onboarding_step = 2
            current_user.last_welcome_shown = datetime.now()  # Set the timestamp when moving to step 2
            db.session.commit()
            
        # Handle step 2 submission (topic preferences)
        elif "step2" in request.form:
            # Process topic preferences
            for key, value in request.form.items():
                if key.startswith('topic_'):
                    _, subject, topic = key.split('_', 2)
                    frequency = int(value)  # -1, 0, or 1
                    
                    # Update or create topic preference
                    pref = TopicPreference.query.filter_by(
                        user_id=current_user.id,
                        subject=subject,
                        topic=topic
                    ).first()
                    
                    if pref:
                        pref.frequency = frequency
                    else:
                        pref = TopicPreference(
                            user_id=current_user.id,
                            subject=subject,
                            topic=topic,
                            frequency=frequency
                        )
                        db.session.add(pref)
            
            current_user.welcome_completed = True
            current_user.last_welcome_shown = datetime.now()
            db.session.commit()
            
            # Only redirect to dashboard if not in settings mode
            if not settings_mode:
                flash("Welcome setup completed! You can now access your personalized dashboard.")
                return redirect(url_for('dashboard'))
            else:
                flash("Settings updated successfully!")
                return redirect(url_for('welcome') + '?settings=true')
    
    return render_template(
        'welcome.html',
        user=current_user,
        curriculum=curriculum_data,
        subject_end_dates=SUBJECT_END_DATES,
        now=datetime.now(),
        settings_mode=settings_mode,
        timedelta=timedelta  # Add timedelta to template context
    )

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
            welcome_completed=False,
            onboarding_step=1
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)  # Auto-login after registration
        return redirect(url_for("welcome"))  # Redirect to welcome page instead of login
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

# Filter timetable tasks based on user's selected subjects
def filter_timetable_for_user(timetable, user):
    """Filter timetable tasks based on user's selected subjects"""
    if not timetable:
        return {}
        
    filtered_timetable = {}
    has_subjects = user.subjects is not None
    
    # Check which subjects the user is taking
    chemistry = has_subjects and user.subjects.chemistry
    biology = has_subjects and user.subjects.biology
    
    for day, day_tasks in timetable.items():
        filtered_day_tasks = []
        for task in day_tasks:
            task_subject = task.split(":")[0].strip()
            # Always include Psychology tasks
            if "Psychology" in task_subject:
                filtered_day_tasks.append(task)
            # Only include Chemistry if user selected it
            elif "Chemistry" in task_subject and (not has_subjects or chemistry):
                filtered_day_tasks.append(task)
            # Only include Biology if user selected it
            elif "Biology" in task_subject and (not has_subjects or biology):
                filtered_day_tasks.append(task)
        
        if filtered_day_tasks:
            filtered_timetable[day] = filtered_day_tasks
    
    return filtered_timetable

# Dashboard: Shows timetable, weekend points system, & Up Learn progress tracker
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST" and "update_progress" in request.form:
        try:
            new_chem = int(request.form.get("chem_progress", 0))
            new_bio_y13 = int(request.form.get("bio_y13_progress", 0))
            new_bio_y12 = int(request.form.get("bio_y12_progress", 0))
            
            # Only update if any values changed
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
    
    # Load curriculum data once
    curriculum_data = load_curriculum()
    
    # Get user's selected subjects
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
        
    # Get daily tasks, filtered timetable, and calendar data
    daily_tasks = generate_daily_tasks(curriculum_data, user_subjects, uplearn_subjects)
    filtered_timetable = filter_timetable_for_user(weekday_timetable, current_user)
    calendar_data = get_calendar_data()
    
    # Find upcoming exams for each subject
    upcoming_exams = {}
    for subject, exams in SUBJECT_END_DATES.items():
        next_exams = sorted(
            [exam for exam in exams if days_until_filter(exam['date']) > 0],
            key=lambda x: days_until_filter(x['date'])
        )
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

@app.route("/study_planner")
@login_required
def study_planner():
    # Get user's selected subjects for task filtering
    user_subjects = []
    if current_user.subjects:
        if current_user.subjects.biology:
            user_subjects.append("Biology")
        if current_user.subjects.chemistry:
            user_subjects.append("Chemistry")
    # Always include Psychology
    curriculum = load_curriculum()
    if "Psychology" in curriculum:
        user_subjects.append("Psychology")
        
    # Filter weekend tasks based on user's selected subjects
    filtered_weekend_tasks = []
    for task in weekend_tasks:
        task_subject = task["task"].split(":")[0].strip()
        if ("Biology" in task_subject and "Biology" in user_subjects) or \
           ("Chemistry" in task_subject and "Chemistry" in user_subjects) or \
           ("Psychology" in task_subject):
            filtered_weekend_tasks.append(task)
    
    # Filter timetable for user's subjects
    filtered_timetable = filter_timetable_for_user(weekday_timetable, current_user)
    
    # Get calendar data for the planner view
    calendar_data = get_calendar_data()
    
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
    return render_template("curriculum.html")
    
@app.route("/study_analytics")
@login_required
def study_analytics():
    # Get task logs for the current user, ordered by most recent
    task_logs = TaskLog.query.filter_by(user_id=current_user.id).order_by(TaskLog.date_completed.desc()).all()
    
    # Get UpLearn logs for the current user
    uplearn_logs = UplearnLog.query.filter_by(user_id=current_user.id).order_by(UplearnLog.date.desc()).all()
    
    # Calculate weekly statistics
    week_stats = calculate_week_stats(task_logs, uplearn_logs)
    
    # Calculate efficiency and productivity metrics
    avg_duration_by_subject = {}
    avg_difficulty_by_subject = {}
    productivity = 0
    
    if task_logs:
        for subject in ['Chemistry', 'Biology Y13', 'Biology Y12', 'Psychology']:
            subject_logs = [log for log in task_logs if log.subject == subject]
            if subject_logs:
                avg_duration_by_subject[subject] = sum(log.duration for log in subject_logs) / len(subject_logs)
                avg_difficulty_by_subject[subject] = sum(log.difficulty for log in subject_logs) / len(subject_logs)
        
        # Calculate productivity score (tasks completed per hour of study)
        total_hours = sum(log.duration for log in task_logs) / 60.0
        productivity = len(task_logs) / total_hours if total_hours > 0 else 0
    
    # Calculate time distribution and productivity metrics
    time_distribution, productivity_by_day, day_productivity = calculate_time_distribution(task_logs, uplearn_logs)
    
    # Get streak information
    current_streak, max_streak = calculate_streak_stats(task_logs)
    
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
    # Get logs for the current user
    task_logs = TaskLog.query.filter_by(user_id=current_user.id).all()
    uplearn_logs = UplearnLog.query.filter_by(user_id=current_user.id).all()
    
    # Use helper functions for calculations
    time_distribution, productivity_by_day, _ = calculate_time_distribution(task_logs, uplearn_logs)
    current_streak, max_streak = calculate_streak_stats(task_logs)
    
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
                duration=int(request.form.get("duration", 30)),
                difficulty=int(request.form.get("difficulty", 3)),
                notes=request.form.get("notes", "")
            )
            db.session.add(new_task)
            db.session.commit()
            flash("Task logged successfully!")
            
        elif "log_uplearn" in request.form:
            # Log UpLearn progress
            new_uplearn = UplearnLog(
                user_id=current_user.id,
                subject=request.form.get("subject"),
                lessons_completed=int(request.form.get("lessons_completed", 0)),
                time_spent=int(request.form.get("time_spent", 0)),
                comprehension=int(request.form.get("comprehension", 3))
            )
            db.session.add(new_uplearn)
            db.session.commit()
            flash("UpLearn progress logged successfully!")
            
        return redirect(url_for("progress_log"))
    
    # Get logs for the current user
    task_logs = TaskLog.query.filter_by(user_id=current_user.id).order_by(TaskLog.date_completed.desc()).all()
    uplearn_logs = UplearnLog.query.filter_by(user_id=current_user.id).order_by(UplearnLog.date.desc()).all()
    
    # Calculate UpLearn statistics
    uplearn_stats = calculate_uplearn_stats(uplearn_logs)
    
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
    """Initialize the database"""
    with app.app_context():
        # Check if tables exist before creating them
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        # Create all tables that don't exist yet
        db.create_all()
        
        # Log which tables were checked
        existing_tables = inspector.get_table_names()
        print(f"Database tables initialized. Found {len(existing_tables)} existing tables.")
        
        # Verify required tables are present
        required_tables = ['user', 'user_subjects', 'task_log', 'uplearn_log', 'topic_preference']
        missing = [table for table in required_tables if table not in existing_tables]
        if missing:
            print(f"Warning: Some required tables were missing and have been created: {', '.join(missing)}")
        else:
            print("All required tables are present.")

def calculate_week_stats(task_logs, uplearn_logs):
    """Calculate weekly study statistics"""
    stats = {
        'total_study_time': 0,
        'tasks_completed': 0,
        'avg_difficulty': 0,
        'uplearn_lessons': 0,
        'uplearn_time': 0,
        'subjects': {}
    }
    
    # Calculate one week ago
    week_ago = datetime.now() - timedelta(days=7)
    
    # Process task logs
    recent_tasks = [log for log in task_logs if log.date_completed >= week_ago]
    if recent_tasks:
        stats['tasks_completed'] = len(recent_tasks)
        stats['total_study_time'] = sum(log.duration for log in recent_tasks)
        stats['avg_difficulty'] = sum(log.difficulty for log in recent_tasks) / len(recent_tasks)
        
        # Calculate per-subject stats
        for log in recent_tasks:
            if log.subject not in stats['subjects']:
                stats['subjects'][log.subject] = {
                    'time': 0,
                    'tasks': 0,
                    'avg_difficulty': 0
                }
            subj_stats = stats['subjects'][log.subject]
            subj_stats['time'] += log.duration
            subj_stats['tasks'] += 1
            subj_stats['avg_difficulty'] = (
                (subj_stats['avg_difficulty'] * (subj_stats['tasks'] - 1) + log.difficulty)
                / subj_stats['tasks']
            )
    
    # Process UpLearn logs
    recent_uplearn = [log for log in uplearn_logs if log.date >= week_ago.date()]
    if recent_uplearn:
        stats['uplearn_lessons'] = sum(log.lessons_completed for log in recent_uplearn)
        stats['uplearn_time'] = sum(log.time_spent for log in recent_uplearn)
    
    return stats

def calculate_time_distribution(task_logs, uplearn_logs):
    """Calculate time distribution and productivity metrics"""
    time_dist = {
        'morning': 0,   # 6-12
        'afternoon': 0, # 12-18
        'evening': 0,   # 18-24
        'night': 0      # 0-6
    }
    
    productivity = {
        'Monday': 0,
        'Tuesday': 0,
        'Wednesday': 0,
        'Thursday': 0,
        'Friday': 0,
        'Saturday': 0,
        'Sunday': 0
    }
    
    day_prod = {
        'tasks_by_day': {},
        'time_by_day': {},
        'efficiency_by_day': {}
    }
    
    # Process task logs
    for log in task_logs:
        hour = log.date_completed.hour
        day = log.date_completed.strftime('%A')
        
        # Time distribution
        if 6 <= hour < 12:
            time_dist['morning'] += log.duration
        elif 12 <= hour < 18:
            time_dist['afternoon'] += log.duration
        elif 18 <= hour < 24:
            time_dist['evening'] += log.duration
        else:
            time_dist['night'] += log.duration
        
        # Day productivity
        if day not in day_prod['tasks_by_day']:
            day_prod['tasks_by_day'][day] = 0
            day_prod['time_by_day'][day] = 0
            
        day_prod['tasks_by_day'][day] += 1
        day_prod['time_by_day'][day] += log.duration
        
    # Calculate efficiency (tasks per hour)
    for day in day_prod['tasks_by_day'].keys():
        hours = day_prod['time_by_day'][day] / 60.0  # Convert minutes to hours
        if hours > 0:
            day_prod['efficiency_by_day'][day] = day_prod['tasks_by_day'][day] / hours
            productivity[day] = day_prod['efficiency_by_day'][day]
        else:
            day_prod['efficiency_by_day'][day] = 0
            productivity[day] = 0
            
    return time_dist, productivity, day_prod

def calculate_streak_stats(task_logs):
    """Calculate current and maximum study streaks"""
    if not task_logs:
        return 0, 0
        
    # Get unique dates of task completion
    dates = sorted(set(log.date_completed.date() for log in task_logs))
    if not dates:
        return 0, 0
        
    current_streak = 0
    max_streak = 0
    temp_streak = 0
    today = datetime.now().date()
    
    # Calculate current streak (must include today or yesterday)
    if dates[-1] >= today - timedelta(days=1):
        current_date = dates[-1]
        i = len(dates) - 1
        while i >= 0 and current_date - dates[i] <= timedelta(days=current_date - dates[i].date()):
            current_streak += 1
            if i > 0:
                current_date = dates[i] - timedelta(days=1)
            i -= 1
            
    # Calculate max streak
    for i in range(len(dates)):
        if i == 0 or (dates[i] - dates[i-1]) == timedelta(days=1):
            temp_streak += 1
        else:
            temp_streak = 1
        max_streak = max(max_streak, temp_streak)
        
    return current_streak, max_streak

def calculate_uplearn_stats(uplearn_logs):
    """Calculate UpLearn statistics"""
    stats = {
        'total_lessons': 0,
        'total_time': 0,
        'avg_comprehension': 0,
        'by_subject': {}
    }
    
    if not uplearn_logs:
        return stats
        
    # Calculate overall stats
    stats['total_lessons'] = sum(log.lessons_completed for log in uplearn_logs)
    stats['total_time'] = sum(log.time_spent for log in uplearn_logs)
    stats['avg_comprehension'] = sum(log.comprehension for log in uplearn_logs) / len(uplearn_logs)
    
    # Calculate per-subject stats
    for log in uplearn_logs:
        if log.subject not in stats['by_subject']:
            stats['by_subject'][log.subject] = {
                'lessons': 0,
                'time': 0,
                'avg_comprehension': 0,
                'logs_count': 0
            }
        
        subj_stats = stats['by_subject'][log.subject]
        subj_stats['lessons'] += log.lessons_completed
        subj_stats['time'] += log.time_spent
        subj_stats['logs_count'] += 1
        subj_stats['avg_comprehension'] = (
            (subj_stats['avg_comprehension'] * (subj_stats['logs_count'] - 1) + log.comprehension)
            / subj_stats['logs_count']
        )
    
    return stats

def get_calendar_data():
    """Get calendar data for the current month"""
    today = datetime.now()
    start_of_month = today.replace(day=1)
    
    # Get the last day of the month
    if today.month == 12:
        end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    calendar_data = {
        'today': today,
        'start_of_month': start_of_month,
        'end_of_month': end_of_month,
        'days': [],
        'weeks': []
    }
    
    # Fill in the days
    current_date = start_of_month
    current_week = []
    
    # Add empty days at the start if month doesn't start on Monday
    first_weekday = start_of_month.weekday()
    if first_weekday > 0:
        for _ in range(first_weekday):
            current_week.append(None)
    
    while current_date <= end_of_month:
        current_week.append(current_date)
        
        # Start new week if Sunday or last day
        if current_date.weekday() == 6 or current_date == end_of_month:
            # Fill in empty days at end of month
            while len(current_week) < 7:
                current_week.append(None)
            calendar_data['weeks'].append(current_week)
            current_week = []
        
        calendar_data['days'].append({
            'date': current_date,
            'is_today': current_date.date() == today.date(),
            'is_weekend': current_date.weekday() >= 5
        })
        current_date += timedelta(days=1)
    
    return calendar_data

def get_uplearn_link(subject):
    """Get the UpLearn link for a given subject"""
    if subject == "Chemistry":
        return "https://uplearn.co.uk/app/chemistry"
    elif subject == "Biology":
        return "https://uplearn.co.uk/app/biology"
    else:
        return "https://uplearn.co.uk/app"

def load_curriculum():
    """Load curriculum data from static/data/curriculum.json"""
    try:
        with open('static/data/curriculum.json', 'r') as f:
            data = json.load(f)
            # Use the simplified Curriculum section from the JSON
            if 'Curriculum' in data:
                return data['Curriculum']
            else:
                # Return a minimal default curriculum if the Curriculum section is missing
                return {
                    "Psychology": [
                        "Research Methods",
                        "Memory",
                        "Social Influence",
                        "Attachment"
                    ],
                    "Chemistry": [
                        "Atomic Structure",
                        "Chemical Bonding",
                        "Energetics"
                    ],
                    "Biology": [
                        "Cell Structure",
                        "Transport Systems",
                        "Cell Division"
                    ]
                }
    except Exception as e:
        print(f"Error loading curriculum data: {e}")
        # Return the same minimal default curriculum if file can't be loaded
        return {
            "Psychology": [
                "Research Methods",
                "Memory",
                "Social Influence",
                "Attachment"
            ],
            "Chemistry": [
                "Atomic Structure",
                "Chemical Bonding",
                "Energetics"
            ],
            "Biology": [
                "Cell Structure",
                "Transport Systems",
                "Cell Division"
            ]
        }

def generate_daily_tasks(curriculum, user_subjects, uplearn_subjects, count=3):
    """Generate daily personalized tasks based on curriculum and user preferences"""
    tasks = []
    
    # Add subject-specific tasks
    for subject in user_subjects:
        if subject not in curriculum:
            continue
            
        # Add subject revision tasks
        for topic in curriculum[subject]:  # Topics are now in a list
            # Basic task formats
            tasks.append({
                "task": f"{subject}: Review {topic} notes",
                "subject": subject,
                "duration": 30,
                "is_uplearn": False
            })
            tasks.append({
                "task": f"{subject}: Practice questions on {topic}",
                "subject": subject,
                "duration": 45,
                "is_uplearn": False
            })
    
    # Add UpLearn tasks for selected subjects
    for subject in uplearn_subjects:
        tasks.append({
            "task": f"{subject}: Complete UpLearn lesson",
            "subject": subject,
            "duration": 60,
            "is_uplearn": True
        })
    
    # If we don't have enough tasks, add generic ones
    while len(tasks) < count:
        tasks.append({
            "task": "General revision session",
            "subject": "General",
            "duration": 45,
            "is_uplearn": False
        })
    
    # Shuffle and return the requested number of tasks
    import random
    random.shuffle(tasks)
    return tasks[:count]

if __name__ == "__main__":
    # Create database only if it doesn't exist
    init_db()
    
    # Handle Python 3.13 compatibility
    python_version = tuple(map(int, platform.python_version_tuple()))
    if (3, 13) <= python_version < (3, 14):
        print("Running with Python 3.13 compatibility mode")
        # Disable reloader and threading for Python 3.13
        app.run(
            debug=True,
            use_reloader=False,
            threaded=False,
            port=5000,
            host='127.0.0.1'
        )
    else:
        # Normal mode for other Python versions
        app.run(
            debug=True,
            port=5000,
            host='127.0.0.1'
        )