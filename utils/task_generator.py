import json
import random
from datetime import datetime
import os

def load_curriculum():
    # Get the absolute path to the curriculum.json file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, 'static', 'data', 'curriculum.json')
    
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

def generate_daily_tasks(curriculum_data, user_subjects=None, uplearn_subjects=None):
    total_daily_minutes = random.randint(180, 240)  # 3-4 hours
    minutes_remaining = total_daily_minutes
    tasks = []
    
    # Get current date to determine exam proximity
    today = datetime.now()
    
    # Select subjects based on user preference or randomly
    if user_subjects and len(user_subjects) > 0:
        # If user has selected subjects, use those
        daily_subjects = [s for s in user_subjects if s in curriculum_data]
        # Ensure we have at least one subject
        if not daily_subjects and curriculum_data:
            daily_subjects = [list(curriculum_data.keys())[0]]
    else:
        # Otherwise, randomly select 2-3 subjects
        subjects = list(curriculum_data.keys())
        daily_subjects = random.sample(subjects, min(random.randint(2, 3), len(subjects)))
    
    for subject in daily_subjects:
        # Allocate time based on remaining minutes
        subject_minutes = minutes_remaining // len(daily_subjects)
        
        # Skip if subject is not in curriculum data
        if subject not in curriculum_data:
            continue
            
        subject_data = curriculum_data[subject]
        
        # Determine if this subject should be Uplearn-oriented (90% chance if uplearn_subjects includes it)
        # Psychology is never uplearn oriented
        is_uplearn_task = False
        if uplearn_subjects and subject in uplearn_subjects and subject != "Psychology" and random.random() < 0.9:
            is_uplearn_task = True
        
        if subject == "Biology":
            # Handle Biology's special structure with Years
            for year in subject_data["Years"]:
                for module in year["Modules"]:
                    if module["Topics"]:
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
                topic = random.choice(paper["Topics"])
                task = generate_task_for_topic(subject, topic, subject_minutes)
                tasks.append(task)
            elif "Modules" in subject_data:  # Chemistry
                module = random.choice(subject_data["Modules"])
                if module["Topics"]:
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
    links = {
        "Chemistry": "https://web.uplearn.co.uk/learn/chemistry-ocr-2",
        "Biology (Year 13)": "https://web.uplearn.co.uk/learn/biology-ocr-2",
        "Biology (Y13)": "https://web.uplearn.co.uk/learn/biology-ocr-2",
        "Biology (Year 12)": "https://web.uplearn.co.uk/learn/biology-ocr-1",
        "Biology (Y12)": "https://web.uplearn.co.uk/learn/biology-ocr-1",
        "Biology": "https://web.uplearn.co.uk/learn/biology-ocr-2"
    }
    return links.get(subject, "")