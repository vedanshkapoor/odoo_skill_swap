import requests
import time
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    filename='test_routes.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:5001"

# Set up retry strategy
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))

def test_register():
    try:
        response = session.post(f"{BASE_URL}/register", json={"name": "Alice", "location": "Delhi"}, timeout=5)
        logger.info(f"Register response: {response.status_code}, {response.json()}")
        if response.status_code == 201:
            return response.json().get('id')
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Register test failed: {str(e)}")
        return None

def test_add_skills(user_id):
    try:
        response = session.post(f"{BASE_URL}/skills", json={"user_id": user_id, "skill_offered": "Python", "skill_wanted": "JavaScript"}, timeout=5)
        logger.info(f"Skills response: {response.status_code}, {response.json()}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Skills test failed: {str(e)}")

def test_get_swaps(user_id):
    try:
        response = session.get(f"{BASE_URL}/swaps?user_id={user_id}", timeout=5)
        logger.info(f"Swaps response: {response.status_code}, {response.json()}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Swaps test failed: {str(e)}")

def test_get_swap(swap_id):
    try:
        response = session.get(f"{BASE_URL}/swaps/{swap_id}", timeout=5)
        logger.info(f"Swap response: {response.status_code}, {response.json()}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Swap test failed: {str(e)}")

def test_add_feedback(swap_id):
    try:
        response = session.post(f"{BASE_URL}/feedback", json={"swap_id": swap_id, "rating": 5, "comment": "Great swap!"}, timeout=5)
        logger.info(f"Feedback response: {response.status_code}, {response.json()}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Feedback test failed: {str(e)}")

if __name__ == "__main__":
    time.sleep(5)  # Wait for Flask server
    user_id = test_register()
    if user_id:
        test_add_skills(user_id)
        test_get_swaps(user_id)
        try:
            response = session.post(f"{BASE_URL}/swaps", json={"from_user_id": user_id, "to_user_id": user_id, "status": "pending"})
            if response.status_code == 201:
                swap_id = response.json().get('id')
                test_get_swap(swap_id)
                test_add_feedback(swap_id)
            else:
                logger.error(f"Swap creation failed: {response.json()}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Swap creation failed: {str(e)}")
    logger.info("Test completed. Check test_routes.log and app.log")