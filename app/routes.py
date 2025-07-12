import logging
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, User, Skill, Swap, Feedback

# Import embedding update
from app.embeddings import update_embeddings_optimized

# Configure logging with explicit file path and handler
log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.log'))
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

# Initialize Flask app
app = Flask(__name__)
CORS(app)
base_dir = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(base_dir, "..", "data", "skill_swap.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()
    logger.debug("Database initialized in routes.py")

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        name = data.get('name')
        location = data.get('location')
        if not name or not location:
            logger.error("Missing name or location in registration")
            return jsonify({"error": "Name and location required"}), 400
        user = User(name=name, location=location)
        db.session.add(user)
        db.session.commit()
        logger.info(f"Registered user: {user}")
        return jsonify({"id": user.id, "name": user.name, "location": user.location}), 201
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/skills', methods=['POST'])
def add_skills():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        skill_offered = data.get('skill_offered')
        skill_wanted = data.get('skill_wanted', None)
        if not user_id or not skill_offered:
            logger.error("Missing user_id or skill_offered")
            return jsonify({"error": "User ID and skill offered required"}), 400

        user = User.query.get(user_id)
        if not user:
            logger.error(f"User not found: {user_id}")
            return jsonify({"error": "User not found"}), 404

        skill = Skill(user_id=user_id, skill_offered=skill_offered, skill_wanted=skill_wanted)
        db.session.add(skill)
        db.session.commit()
        logger.info(f"Added skill for user {user_id}: {skill_offered}")

        # ✅ Update embeddings
        update_embeddings_optimized()
        logger.info("[OK] Embeddings updated after adding skill")

        return jsonify({"message": "Skill added", "skill_id": skill.id}), 201
    except Exception as e:
        logger.error(f"Skills addition error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/swaps', methods=['GET'])
def get_swaps():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            logger.error("Missing user_id for swaps")
            return jsonify({"error": "User ID required"}), 400
        swaps = Swap.query.filter((Swap.from_user_id == user_id) | (Swap.to_user_id == user_id)).all()
        result = [{"id": s.id, "from_user_id": s.from_user_id, "to_user_id": s.to_user_id, "status": s.status} for s in swaps]
        logger.info(f"Retrieved swaps for user {user_id}")
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Swaps retrieval error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/swaps', methods=['POST'])
def add_swap():
    try:
        data = request.get_json()
        from_user_id = data.get('from_user_id')
        to_user_id = data.get('to_user_id')
        status = data.get('status', 'pending')
        if not from_user_id or not to_user_id:
            logger.error("Missing from_user_id or to_user_id")
            return jsonify({"error": "From and to user IDs required"}), 400
        from_user = User.query.get(from_user_id)
        to_user = User.query.get(to_user_id)
        if not from_user or not to_user:
            logger.error(f"User not found: from_user_id={from_user_id}, to_user_id={to_user_id}")
            return jsonify({"error": "User not found"}), 404
        swap = Swap(from_user_id=from_user_id, to_user_id=to_user_id, status=status)
        db.session.add(swap)
        db.session.commit()
        logger.info(f"Added swap: {swap}")
        return jsonify({"id": swap.id, "from_user_id": swap.from_user_id, "to_user_id": swap.to_user_id, "status": swap.status}), 201
    except Exception as e:
        logger.error(f"Swap creation error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/swaps/<int:id>', methods=['GET'])
def get_swap(id):
    try:
        swap = Swap.query.get(id)
        if not swap:
            logger.error(f"Swap not found: {id}")
            return jsonify({"error": "Swap not found"}), 404
        logger.info(f"Retrieved swap: {id}")
        return jsonify({"id": swap.id, "from_user_id": swap.from_user_id, "to_user_id": swap.to_user_id, "status": swap.status}), 200
    except Exception as e:
        logger.error(f"Swap retrieval error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/feedback', methods=['POST'])
def add_feedback():
    try:
        data = request.get_json()
        swap_id = data.get('swap_id')
        rating = data.get('rating')
        comment = data.get('comment', None)
        if not swap_id or not rating:
            logger.error("Missing swap_id or rating")
            return jsonify({"error": "Swap ID and rating required"}), 400
        feedback = Feedback(swap_id=swap_id, rating=rating, comment=comment)
        db.session.add(feedback)
        db.session.commit()
        logger.info(f"Added feedback for swap {swap_id}")
        return jsonify({"message": "Feedback added", "feedback_id": feedback.id}), 201
    except Exception as e:
        logger.error(f"Feedback error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5001, debug=True)
