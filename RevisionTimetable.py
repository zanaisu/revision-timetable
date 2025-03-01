import sys
import subprocess
import os
import platform

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
        # Try to use importlib_metadata to check installed packages (more modern approach)
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

# Add verification before other imports
if verify_dependencies():
    from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
    from markupsafe import Markup
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy.pool import NullPool
    from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
    from werkzeug.security import generate_password_hash, check_password_hash
    import os
    from datetime import datetime, timedelta
    from utils.task_generator import load_curriculum, generate_daily_tasks, get_uplearn_link

    # Initialize Flask and extensions
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "your_secret_key_here"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Use NullPool to avoid greenlet dependency issues with Python 3.13
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"poolclass": NullPool}

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
        task_logs = db.relationship('TaskLog', backref='user', lazy=True)
        uplearn_logs = db.relationship('UplearnLog', backref='user', lazy=True)

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
        """Generate calendar data with exam dates for the next 15 weeks"""
        if not start_date:
            start_date = datetime.now().date()
        elif isinstance(start_date, datetime):
            start_date = start_date.date()
        
        weeks = []
        current_date = start_date - timedelta(days=start_date.weekday())  # Start from Monday
        
        # Create a map of exam dates for efficient lookup
        important_dates = {}
        for subject, exams in SUBJECT_END_DATES.items():
            for exam in exams:
                exam_date = exam['date']
                important_dates.setdefault(exam_date, []).append({
                    'subject': subject, 
                    'exam': exam['paper'], 
                    'topics': exam['topics']
                })
        
        # Generate 15 weeks of data
        for week_num in range(1, 16):
            week_end = current_date + timedelta(days=6)
            week_data = {
                'week_number': week_num,
                'start_date': current_date.strftime('%Y-%m-%d'),
                'end_date': week_end.strftime('%Y-%m-%d'),
                'subjects': {},
                'days': [],
                'exams': []
            }
            
            # Generate daily data
            for day_offset in range(7):
                day_date = current_date + timedelta(days=day_offset)
                day_str = day_date.strftime('%Y-%m-%d')
                day_name = day_date.strftime('%A')
                
                # Get exams for this day
                day_exams = important_dates.get(day_str, [])
                
                # Add day data
                day_data = {
                    'date': day_str,
                    'day_name': day_name,
                    'tasks': weekday_timetable.get(day_name, []),
                    'exams': day_exams
                }
                
                week_data['days'].append(day_data)
                week_data['exams'].extend(day_exams)
            
            # Add upcoming exam info for each subject
            for subject, exams in SUBJECT_END_DATES.items():
                # Find the next exam
                next_exam = None
                for exam in sorted(exams, key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d')):
                    exam_date = datetime.strptime(exam['date'], '%Y-%m-%d').date()
                    if exam_date >= current_date:
                        next_exam = exam
                        break
                
                if next_exam:
                    week_data['subjects'][subject] = {
                        'tasks': weekday_timetable.get(current_date.strftime('%A'), []),
                        'end_date': next_exam['date'],
                        'next_exam': next_exam
                    }
            
            weeks.append(week_data)
            current_date += timedelta(days=7)
        
        return weeks


    # ---------------------------
    # Helper functions for analytics
    # ---------------------------
    def calculate_time_distribution(task_logs, uplearn_logs):
        """Calculate time spent per day of the week"""
        time_distribution = {day: 0 for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
        day_productivity = {day: {'time': 0, 'tasks': 0} for day in time_distribution}
        
        # Add task time
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
            hours = data['time'] / 60.0 if data['time'] > 0 else 0
            productivity_by_day[day] = data['tasks'] / hours if hours > 0 else 0
            
        return time_distribution, productivity_by_day, day_productivity

    def calculate_streak_stats(task_logs):
        """Calculate current and max streak from task logs"""
        if not task_logs:
            return 0, 0
            
        current_date = datetime.now().date()
        
        # Check if there's a log from today
        today_log = any(log.date_completed.date() == current_date for log in task_logs)
        if not today_log:
            current_streak = 0
            # Check yesterday
            yesterday = current_date - timedelta(days=1)
            if any(log.date_completed.date() == yesterday for log in task_logs):
                current_streak = 1
        else:
            current_streak = 1
        
        # Calculate max streak
        streak_dates = sorted(set(log.date_completed.date() for log in task_logs))
        
        if streak_dates:
            max_streak = 1
            current_streak_count = 1
            
            for i in range(1, len(streak_dates)):
                if (streak_dates[i] - streak_dates[i-1]).days == 1:
                    current_streak_count += 1
                else:
                    max_streak = max(max_streak, current_streak_count)
                    current_streak_count = 1
                    
            # Check the last streak
            max_streak = max(max_streak, current_streak_count)
            
            # If today is part of the streak, update current_streak
            if today_log or (not today_log and any(log.date_completed.date() == yesterday for log in task_logs)):
                i = len(streak_dates) - 1
                current_streak = 1
                while i > 0:
                    if (streak_dates[i] - streak_dates[i-1]).days == 1:
                        current_streak += 1
                        i -= 1
                    else:
                        break
        else:
            max_streak = 0
            
        return current_streak, max_streak

    def calculate_week_stats(task_logs, uplearn_logs, num_weeks=12):
        """Calculate weekly statistics for tasks and uplearn progress"""
        week_stats = {}
        today = datetime.now().date()
        
        for i in range(num_weeks):
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
            
        return week_stats

    def calculate_uplearn_stats(uplearn_logs):
        """Calculate UpLearn statistics for daily and weekly progress"""
        uplearn_stats = {
            "Chemistry": {"daily": [], "weekly": []},
            "Biology Y12": {"daily": [], "weekly": []},
            "Biology Y13": {"daily": [], "weekly": []}
        }
        
        today = datetime.now().date()
        
        # Process daily stats (last 14 days)
        day_range = [today - timedelta(days=i) for i in range(14)]
        
        # Process weekly stats (last 8 weeks)
        week_ranges = []
        for i in range(8):
            week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            week_ranges.append((
                week_start, 
                week_end, 
                f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}"
            ))
        
        # Populate statistics for each subject
        for subject in uplearn_stats:
            # Daily stats
            for day in day_range:
                logs = [log for log in uplearn_logs if log.subject == subject and log.date == day]
                daily_lessons = sum(log.lessons_completed for log in logs)
                uplearn_stats[subject]["daily"].append({
                    "date": day.strftime("%Y-%m-%d"),
                    "lessons": daily_lessons
                })
            
            # Weekly stats
            for week_start, week_end, week_label in week_ranges:
                logs = [
                    log for log in uplearn_logs 
                    if log.subject == subject and week_start <= log.date <= week_end
                ]
                weekly_lessons = sum(log.lessons_completed for log in logs)
                uplearn_stats[subject]["weekly"].append({
                    "week": week_label,
                    "lessons": weekly_lessons
                })
        
        return uplearn_stats

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
            required_tables = ['user', 'user_subjects', 'task_log', 'uplearn_log']
            missing = [table for table in required_tables if table not in existing_tables]
            if missing:
                print(f"Warning: Some required tables were missing and have been created: {', '.join(missing)}")
            else:
                print("All required tables are present.")

    if __name__ == "__main__":
        # Create database only if it doesn't exist
        init_db()
        app.run(debug=True)