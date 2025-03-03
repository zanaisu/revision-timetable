# Revision Timetable

A streamlined study planner application built with Flask to help students organize their revision for A-level subjects (Biology, Chemistry, and Psychology).

## Features

- Personalized study plans based on selected subjects
- Progress tracking for UpLearn and study sessions
- Calendar view with upcoming exam dates
- Weekend task point system
- Detailed study analytics and time analysis
- Customizable dashboard

## Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the application: `python app.py`

## Development

The application is built with:
- Flask web framework
- SQLAlchemy for database operations
- Flask-Login for user authentication
- Bootstrap for frontend UI

## Deployment

For production deployment, use Gunicorn:

```
gunicorn -c gunicorn.conf.py app:app
```

## Project Structure

```
/
├── app.py                  # Main application file
├── requirements.txt        # Dependencies
├── gunicorn.conf.py        # Gunicorn configuration
├── instance/               # Database and instance-specific files
│   └── site.db             # SQLite database
├── static/
│   ├── css/                # CSS stylesheets
│   ├── data/               # Application data (curriculum.json)
│   └── js/                 # JavaScript files
└── templates/              # HTML templates
    ├── base.html           # Base template
    ├── components/         # Reusable template components
    ├── dashboard.html      # Main dashboard
    └── ...                 # Other template files
```

## Usage

1. Register a new account
2. Complete the onboarding process to select your subjects
3. View your personalized dashboard with study tasks
4. Log completed tasks and track your progress
5. View analytics to optimize your study habits