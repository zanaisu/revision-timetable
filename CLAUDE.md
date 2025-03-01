# Revision Timetable Project Guide

## Build Commands
- Run development server: `python RevisionTimetable.py`
- Deploy with Gunicorn: `gunicorn -c gunicorn.conf.py RevisionTimetable:app`

## Code Style Guidelines
- **Python**: PEP 8 compliant, 4 spaces indentation
- **Imports**: Group by standard library, third-party, then local
- **Naming**: 
  - Variables/Functions: snake_case
  - Classes: PascalCase
  - Routes: snake_case
- **Error Handling**: Use try/except with specific exceptions
- **Documentation**: Docstrings for functions and classes
- **Templates**: Follow Flask Jinja2 pattern with base inheritance

## Project Structure
- Flask MVC architecture (routes in main file, templates for views)
- CSS in static/css, JavaScript in static/js
- Modular JavaScript files for different features
- Templates folder for HTML with components subfolder

## Commit Guidelines
- Clear, concise commit messages describing the change
- Reference issue numbers when applicable