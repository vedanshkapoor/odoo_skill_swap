import logging
import os
import pdfplumber
from app.models import db, Skill, User, init_db  # Import models for direct DB access
from flask import Flask  # For app context, but not as a full app

# Set up logging
log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app.log'))  # Adjusted to project root
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

# Initialize Flask app for DB context
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(os.path.dirname(__file__), "..", "..", "data", "skill_swap.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def extract_skills_from_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "".join(page.extract_text() for page in pdf.pages if page.extract_text())
            # Simple skill extraction (customize based on resume format)
            skills = []
            common_skills = ['python', 'java', 'sql', 'html', 'css', 'javascript']  # Example skill list
            for skill in common_skills:
                if skill.lower() in text.lower():
                    skills.append(skill.capitalize())
            logger.debug(f"Extracted skills from {pdf_path}: {skills}")
            return skills
    except Exception as e:
        logger.error(f"Error extracting skills from {pdf_path}: {str(e)}")
        return []

def process_resumes():
    resumes_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'resumes')
    resumes_dir = os.path.abspath(resumes_dir)  # Convert to absolute path for clarity
    logger.info(f"Processing resumes from directory: {resumes_dir}")
    if not os.path.exists(resumes_dir):
        os.makedirs(resumes_dir)
        logger.debug(f"Created resumes directory: {resumes_dir}")

    with app.app_context():
        # Ensure tables exist
        inspector = db.inspect(db.engine)
        if not inspector.has_table('users'):
            db.create_all()
            logger.info("Created database tables as they were missing")
        else:
            logger.debug("Database tables already exist")

        init_db()  # Ensure consistency with models.py
        for filename in os.listdir(resumes_dir):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(resumes_dir, filename)
                skills = extract_skills_from_pdf(pdf_path)
                if skills:
                    user = User.query.first()  # Check for existing user
                    if not user:
                        logger.warning("No users found, creating a default user")
                        user = User(name="DefaultUser", location="Unknown")
                        db.session.add(user)
                        db.session.commit()
                    user_id = user.id
                    for skill in skills:
                        existing_skill = Skill.query.filter_by(user_id=user_id, skill_offered=skill).first()
                        if not existing_skill:
                            new_skill = Skill(user_id=user_id, skill_offered=skill)
                            db.session.add(new_skill)
                    db.session.commit()
                    logger.info(f"Processed resume {filename} and added skills for user {user_id}")

if __name__ == '__main__':
    # Test the script independently
    logger.info("Extract_skills.py test starting.")
    process_resumes()
    logger.info("Extract_skills.py test completed. Check app.log and data/resumes/ for results.")