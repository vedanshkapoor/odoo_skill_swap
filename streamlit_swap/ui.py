import streamlit as st
import requests
import json
import pdfplumber
import os

st.set_page_config(page_title="Skill Swap Platform", layout="wide")

API_BASE = "http://localhost:5001"
RESUME_DIR = "data/resumes"

st.sidebar.title("📂 Skill Swap Navigation")
page = st.sidebar.radio("Go to", [
    "🏠 Home",
    "📝 Register",
    "📤 Upload Resume",
    "💼 Add Skill",
    "🔁 Swap Match",
    "🤝 Suggested Swaps",
    "📜 View Swaps"
])

if page == "🏠 Home":
    st.title("🔁 Welcome to Skill Swap Platform")
    st.markdown("Use the sidebar to navigate through the app features.")

elif page == "📝 Register":
    st.title("📝 Register New User")
    with st.form("register_form"):
        name = st.text_input("Name")
        location = st.text_input("Location")
        submitted = st.form_submit_button("Register")
        if submitted:
            if name and location:
                res = requests.post(f"{API_BASE}/register", json={"name": name, "location": location})
                if res.status_code == 201:
                    st.success(f"Registered successfully. Your ID: {res.json()['id']}")
                else:
                    st.error(f"Failed to register: {res.json().get('error')}")
            else:
                st.warning("Name and location required.")

elif page == "📤 Upload Resume":
    st.title("📤 Upload Resume to Extract Skills")
    uploaded = st.file_uploader("Upload a PDF resume", type="pdf")
    if uploaded:
        os.makedirs(RESUME_DIR, exist_ok=True)
        path = os.path.join(RESUME_DIR, uploaded.name)
        with open(path, "wb") as f:
            f.write(uploaded.read())
        st.success("Resume uploaded!")

        # Extract skills from PDF
        common_skills = ["python", "machine learning", "deep learning", "data science", "sql", "flask", "streamlit", "nlp", "computer vision"]
        extracted = []
        with pdfplumber.open(path) as pdf:
            text = " ".join([page.extract_text() or "" for page in pdf.pages]).lower()
            extracted = [skill for skill in common_skills if skill in text]

        if extracted:
            st.subheader("✅ Extracted Skills:")
            st.write(", ".join(extracted))
        else:
            st.warning("No known skills found in resume.")

elif page == "💼 Add Skill":
    st.title("💼 Add Your Skills")
    with st.form("add_skill_form"):
        user_id = st.number_input("Your User ID", min_value=1, step=1)
        skill_offered = st.text_input("Skill you can teach")
        skill_wanted = st.text_input("Skill you want to learn (optional)")
        submitted = st.form_submit_button("Add Skill")
        if submitted:
            res = requests.post(f"{API_BASE}/skills", json={
                "user_id": user_id,
                "skill_offered": skill_offered,
                "skill_wanted": skill_wanted
            })
            if res.status_code == 201:
                st.success("Skill added successfully.")
            else:
                st.error(f"Failed to add skill: {res.json().get('error')}")

elif page == "🔁 Swap Match":
    st.title("🔁 Find a Skill Match and Send Swap")
    with st.form("match_form"):
        from_user = st.number_input("Your User ID", min_value=1, step=1)
        to_user = st.number_input("Target User ID to Swap With", min_value=1, step=1)
        submitted = st.form_submit_button("Send Swap Request")
        if submitted:
            if from_user == to_user:
                st.error("You cannot send a swap request to yourself!")
            else:
                res = requests.post(f"{API_BASE}/swaps", json={
                    "from_user_id": from_user,
                    "to_user_id": to_user
                })
                if res.status_code == 201:
                    st.success("Swap request sent!")
                else:
                    st.error(f"Error: {res.json().get('error')}")

elif page == "🤝 Suggested Swaps":
    st.title("🤝 Suggested Users to Swap With")
    user_id = st.number_input("Enter your User ID", min_value=1, step=1)
    if user_id:
        try:
            all_users = requests.get(f"{API_BASE}/register").json()
            your_swaps = requests.get(f"{API_BASE}/swaps", params={"user_id": user_id}).json()
            swapped_ids = set(s['to_user_id'] for s in your_swaps if s['from_user_id'] == user_id)
            possible = [u for u in all_users if u['id'] != user_id and u['id'] not in swapped_ids]
            st.subheader("You can send swaps to:")
            for u in possible:
                st.markdown(f"- {u['name']} (ID: {u['id']}, {u['location']})")
            if not possible:
                st.info("No new users available for swap.")
        except Exception as e:
            st.error(f"Error loading users: {e}")

elif page == "📜 View Swaps":
    st.title("📜 Your Swaps")
    user_id = st.number_input("Enter your User ID to view swaps", min_value=1, step=1)
    if user_id:
        try:
            res = requests.get(f"{API_BASE}/swaps", params={"user_id": user_id})
            if res.status_code == 200:
                swaps = res.json()
                if swaps:
                    for s in swaps:
                        st.write(f"Swap ID: {s['id']} | From: {s['from_user_id']} | To: {s['to_user_id']} | Status: {s['status']}")
                else:
                    st.info("No swaps found.")
            else:
                st.error(f"Failed to load swaps: {res.json().get('error')}")
        except Exception as e:
            st.error(f"Request failed: {e}")
