import logging
import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
db = SQLAlchemy()


# User Model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, location={self.location})>"


# Skill Model
class Skill(db.Model):
    __tablename__ = 'skills'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skill_offered = db.Column(db.String(50), nullable=False)
    skill_wanted = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<Skill(id={self.id}, user_id={self.user_id}, skill_offered={self.skill_offered}, skill_wanted={self.skill_wanted})>"


# Swap Model
class Swap(db.Model):
    __tablename__ = 'swaps'
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(10), default='pending')

    def __repr__(self):
        return f"<Swap(id={self.id}, from_user_id={self.from_user_id}, to_user_id={self.to_user_id}, status={self.status})>"


# Feedback Model
class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    swap_id = db.Column(db.Integer, db.ForeignKey('swaps.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"<Feedback(id={self.id}, swap_id={self.swap_id}, rating={self.rating}, comment={self.comment})>"


# Debug function to initialize and verify database
def init_db(app=None):
    if app is None:
        # Create a temporary app for standalone testing
        app = Flask(__name__)
        # Use absolute path to ensure correct location
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, '..', 'data')
        db_path = os.path.join(data_dir, 'skill_swap.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)

    # Ensure data directory exists and is writable
    data_dir = os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    try:
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger.debug(f"Created data directory: {data_dir}")
        elif not os.access(data_dir, os.W_OK):
            raise PermissionError(f"Directory {data_dir} is not writable")
        # Test write access
        test_file = os.path.join(data_dir, 'test_write.txt')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.debug(f"Verified write access to {data_dir}")
    except PermissionError as e:
        logger.error(f"Permission error creating or accessing directory: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Directory access test failed: {str(e)}")
        raise

    try:
        with app.app_context():
            db.create_all()
            logger.debug("Database tables created successfully")
            # Verify table creation
            if User.query.first() is None:
                logger.debug("User table is empty, creation successful")
            else:
                logger.warning("User table has existing data")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


if __name__ == '__main__':
    # Test the models and database creation independently
    init_db()
    logger.info("Models.py test completed. Check data/skill_swap.db for database file.")