import logging
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from app.models import db, User, Skill, Swap, Feedback
from app.embeddings import update_embeddings_optimized

# Configure logging
log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.log'))
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Initialize Flask app
app = Flask(__name__)
CORS(app)
base_dir = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(base_dir, "..", "data", "skill_swap.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    logger.debug("Database initialized in routes.py")

# ✅ List all users
@app.route('/register', methods=['GET'])
def list_users():
    try:
        users = User.query.all()
        return jsonify([
            {"id": u.id, "name": u.name, "location": u.location}
            for u in users
        ]), 200
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ✅ Register user (idempotent)
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        name = data.get('name')
        location = data.get('location')
        if not name or not location:
            return jsonify({"error": "Name and location required"}), 400

        existing = User.query.filter_by(name=name, location=location).first()
        if existing:
            return jsonify({"id": existing.id, "name": existing.name, "location": existing.location}), 200

        user = User(name=name, location=location)
        db.session.add(user)
        db.session.commit()
        logger.info(f"Registered user: {user}")
        return jsonify({"id": user.id, "name": user.name, "location": user.location}), 201
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ✅ Add skill
@app.route('/skills', methods=['POST'])
def add_skills():
    try:
        data = request.get_json()
        user_id = int(data.get('user_id'))
        skill_offered = data.get('skill_offered')
        skill_wanted = data.get('skill_wanted', None)

        if not user_id or not skill_offered:
            return jsonify({"error": "User ID and skill offered required"}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        skill = Skill(user_id=user_id, skill_offered=skill_offered, skill_wanted=skill_wanted)
        db.session.add(skill)
        db.session.commit()

        update_embeddings_optimized()
        logger.info(f"Added skill for user {user_id}: {skill_offered}")
        return jsonify({"message": "Skill added", "skill_id": skill.id}), 201
    except Exception as e:
        logger.error(f"Skill error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ✅ View swaps
@app.route('/swaps', methods=['GET'])
def get_swaps():
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"error": "User ID required"}), 400

        swaps = Swap.query.filter(
            (Swap.from_user_id == user_id) | (Swap.to_user_id == user_id)
        ).all()

        return jsonify([
            {"id": s.id, "from_user_id": s.from_user_id, "to_user_id": s.to_user_id, "status": s.status}
            for s in swaps
        ]), 200
    except Exception as e:
        logger.error(f"Swaps retrieval error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ✅ Create new swap
@app.route('/swaps', methods=['POST'])
def add_swap():
    try:
        data = request.get_json()
        from_user_id = int(data.get('from_user_id'))
        to_user_id = int(data.get('to_user_id'))
        status = data.get('status', 'pending')

        if not from_user_id or not to_user_id:
            return jsonify({"error": "From and to user IDs required"}), 400

        if from_user_id == to_user_id:
            return jsonify({"error": "Cannot create a swap with yourself"}), 400

        from_user = User.query.get(from_user_id)
        to_user = User.query.get(to_user_id)
        if not from_user or not to_user:
            return jsonify({"error": "User not found"}), 404

        swap = Swap(from_user_id=from_user_id, to_user_id=to_user_id, status=status)
        db.session.add(swap)
        db.session.commit()

        return jsonify({
            "id": swap.id,
            "from_user_id": swap.from_user_id,
            "to_user_id": swap.to_user_id,
            "status": swap.status
        }), 201
    except Exception as e:
        logger.error(f"Swap creation error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ✅ View one swap
@app.route('/swaps/<int:id>', methods=['GET'])
def get_swap(id):
    try:
        swap = Swap.query.get(id)
        if not swap:
            return jsonify({"error": "Swap not found"}), 404
        return jsonify({
            "id": swap.id,
            "from_user_id": swap.from_user_id,
            "to_user_id": swap.to_user_id,
            "status": swap.status
        }), 200
    except Exception as e:
        logger.error(f"Swap retrieval error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ✅ Add feedback
@app.route('/feedback', methods=['POST'])
def add_feedback():
    try:
        data = request.get_json()
        swap_id = data.get('swap_id')
        rating = data.get('rating')
        comment = data.get('comment', None)

        if not swap_id or not rating:
            return jsonify({"error": "Swap ID and rating required"}), 400

        feedback = Feedback(swap_id=swap_id, rating=rating, comment=comment)
        db.session.add(feedback)
        db.session.commit()
        return jsonify({"message": "Feedback added", "feedback_id": feedback.id}), 201
    except Exception as e:
        logger.error(f"Feedback error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5001, debug=True)
