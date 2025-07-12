# 🔁 Skill Swap Platform

## 🧠 Problem Statement

Many learners and professionals possess valuable skills but lack access to affordable learning resources for acquiring new ones. Online learning platforms are often expensive or impersonal, and community learning is rarely structured. 

What if you could **learn a skill by teaching another?**  
This project proposes a **Skill Swap Platform** where users can **exchange knowledge directly** by offering one skill and requesting another — all facilitated by an intelligent matching system.

---

## 🚀 Project Overview

The **Skill Swap Platform** enables users to:
- **Register themselves** with basic details
- **Upload a resume (PDF)** to auto-extract skills
- **List skills they can teach**
- **List skills they want to learn**
- **View suggested users to swap with**
- **Send swap requests**
- **Accept or reject requests**
- **Leave feedback after a successful swap**

The goal is to **democratize learning**, especially in communities or groups where mutual knowledge exchange is preferred over paid tutoring.

---

## 🎯 Key Features

| Feature                             | Description |
|-------------------------------------|-------------|
| 📝 User Registration                | Register with name and location |
| 📤 Resume Upload                    | Upload a PDF resume and extract skills automatically using `pdfplumber` |
| 💼 Skill Management                 | Add skills offered and skills wanted |
| 🤝 Skill Swapping                  | Send swap requests to others based on skill matches |
| 🔍 Suggested Swaps                  | See recommended users to connect with using embedding similarity |
| 📜 Swap Tracker                     | View current, pending, or accepted swaps |
| ⭐ Feedback System                  | Rate and comment on completed swaps (backend ready) |
| 🧠 Semantic Matching                | Skills are embedded via Ollama LLMs and indexed using FAISS for accurate similarity-based recommendations |
| 🔀 Dual DB Architecture             | SQLite for users, FAISS for skill matching |
| 🌐 Fullstack MVP                    | Built with Flask (API) + Streamlit (UI) |

---

## 🏗️ System Architecture

