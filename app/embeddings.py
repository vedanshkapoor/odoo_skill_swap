import logging
import os
import numpy as np
from app.models import db, Skill
from flask import Flask
import faiss
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Set up logging
log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.log'))
os.makedirs(os.path.dirname(log_file), exist_ok=True)
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(console_handler)

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(os.path.dirname(__file__), "..", "data", "skill_swap.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

OLLAMA_URL = "http://localhost:11434/api"

def check_ollama_availability():
    try:
        response = requests.get(f"{OLLAMA_URL}/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m["name"].split(":")[0] for m in models]
            required = ["phi3", "mxbai-embed-large"]
            missing = [m for m in required if m not in model_names]

            if missing:
                logger.error(f"Missing models: {missing}")
                return False

            logger.info("[OK] Ollama server and models available")
            return True
        else:
            logger.error(f"Ollama server error: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Ollama check failed: {str(e)}")
        return False

def generate_batch_descriptions(skills, batch_size=5):
    descriptions = {}

    for i in range(0, len(skills), batch_size):
        batch = skills[i:i + batch_size]
        batch_text = "\n".join([f"{j + 1}. {skill}" for j, skill in enumerate(batch)])

        logger.info(f"Generating descriptions for batch {i // batch_size + 1}/{(len(skills) + batch_size - 1) // batch_size}")

        try:
            url = f"{OLLAMA_URL}/generate"
            headers = {"Content-Type": "application/json"}
            data = {
                "model": "phi3",
                "prompt": f"""Provide brief descriptions for these skills (one sentence each):
{batch_text}

Format your response as:
1. [Skill]: [Description]
2. [Skill]: [Description]
etc.""",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 200,
                    "top_k": 3,
                    "top_p": 0.8
                }
            }

            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)

            if response.status_code == 200:
                result = response.json()
                batch_descriptions = result.get("response", "").strip()
                lines = batch_descriptions.split('\n')
                for line in lines:
                    line = line.strip()
                    if ':' in line and any(char.isdigit() for char in line[:5]):
                        try:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                skill_part = parts[0].strip().split('.', 1)[-1].strip().strip('[]')
                                desc_part = parts[1].strip()
                                for skill in batch:
                                    if skill.lower() in skill_part.lower() or skill_part.lower() in skill.lower():
                                        descriptions[skill] = desc_part
                                        break
                        except:
                            continue

                logger.debug(f"Parsed {len([k for k in descriptions.keys() if k in batch])} descriptions from batch")
            else:
                logger.error(f"Batch description generation failed: {response.status_code}")
                for skill in batch:
                    descriptions[skill] = generate_single_description(skill)
        except Exception as e:
            logger.error(f"Error in batch description generation: {str(e)}")
            for skill in batch:
                descriptions[skill] = generate_single_description(skill)

    for skill in skills:
        if skill not in descriptions:
            logger.warning(f"Missing description for {skill}, generating individually")
            descriptions[skill] = generate_single_description(skill)

    return descriptions

def generate_single_description(skill):
    try:
        url = f"{OLLAMA_URL}/generate"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "phi3",
            "prompt": f"Describe the skill '{skill}' in one sentence.",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 30,
                "top_k": 3
            }
        }
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=8)
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip() or skill
        return skill
    except Exception as e:
        logger.warning(f"Single description generation failed for {skill}: {str(e)}")
        return skill

def generate_single_embedding(skill_description_pair):
    skill, description = skill_description_pair
    try:
        url = f"{OLLAMA_URL}/embeddings"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "mxbai-embed-large",
            "prompt": description
        }
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)
        if response.status_code == 200:
            result = response.json()
            embedding = result.get("embedding")
            return (skill, embedding) if embedding else (skill, None)
        return skill, None
    except Exception as e:
        logger.error(f"Error generating embedding for {skill}: {str(e)}")
        return skill, None

def generate_embeddings_optimized(skills, max_workers=3):
    if not check_ollama_availability():
        return np.array([], dtype=np.float32), []

    try:
        logger.info(f"Generating descriptions for {len(skills)} skills in batches...")
        start_time = time.time()
        descriptions = generate_batch_descriptions(skills)
        desc_time = time.time() - start_time
        logger.info(f"[OK] Description generation completed in {desc_time:.2f} seconds")

        logger.info(f"Generating embeddings using {max_workers} workers...")
        skill_description_pairs = [(skill, descriptions[skill]) for skill in skills]

        embeddings = []
        processed_skills = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_skill = {executor.submit(generate_single_embedding, pair): pair[0] for pair in skill_description_pairs}

            for i, future in enumerate(as_completed(future_to_skill), 1):
                skill_name = future_to_skill[future]
                try:
                    skill, embedding = future.result()
                    if embedding:
                        embeddings.append(embedding)
                        processed_skills.append(skill)
                        logger.info(f"[OK] Embedding {i}/{len(skills)}: {skill}")
                    else:
                        logger.error(f"Embedding failed for {skill}")
                        return np.array([], dtype=np.float32), []
                except Exception as e:
                    logger.error(f"Embedding error for {skill_name}: {str(e)}")
                    return np.array([], dtype=np.float32), []

        if not embeddings:
            logger.error("No embeddings generated")
            return np.array([], dtype=np.float32), []

        embeddings_array = np.array(embeddings, dtype=np.float32)
        embedding_time = time.time() - start_time - desc_time
        logger.info(f"[OK] Generated {len(embeddings)} embeddings in {embedding_time:.2f} seconds")

        return embeddings_array, processed_skills
    except Exception as e:
        logger.error(f"Error in optimized embedding generation: {str(e)}")
        return np.array([], dtype=np.float32), []

def build_faiss_index(embeddings):
    try:
        if embeddings.size == 0:
            return None

        dimension = embeddings.shape[1]
        logger.info(f"Building FAISS index: {embeddings.shape[0]} vectors, {dimension}D")

        index = faiss.IndexFlatIP(dimension)
        faiss.normalize_L2(embeddings)
        index.add(embeddings)

        index_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'embeddings', 'skill_index.faiss')
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        faiss.write_index(index, index_path)

        logger.info(f"[OK] FAISS index saved to {index_path}")
        return index
    except Exception as e:
        logger.error(f"Error building FAISS index: {str(e)}")
        return None

def update_embeddings_optimized():
    try:
        with app.app_context():
            all_skills = [skill.skill_offered for skill in Skill.query.all()]
            if not all_skills:
                logger.warning("No skills found in database")
                return None, []

            unique_skills = []
            seen = set()
            for skill in all_skills:
                skill_clean = skill.strip()
                if skill_clean and skill_clean.lower() not in seen:
                    seen.add(skill_clean.lower())
                    unique_skills.append(skill_clean)

            logger.info(f"Total: {len(all_skills)} skills, Unique: {len(unique_skills)} skills")
            logger.info(f"Processing skills: {unique_skills}")

            total_start = time.time()
            embeddings, processed_skills = generate_embeddings_optimized(unique_skills)

            if embeddings.size == 0:
                logger.error("Failed to generate embeddings")
                return None, []

            index = build_faiss_index(embeddings)
            if index is None:
                logger.error("Failed to build FAISS index")
                return None, []

            skills_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'embeddings', 'skills.json')
            with open(skills_path, 'w') as f:
                json.dump(processed_skills, f, indent=2)

            total_time = time.time() - total_start
            logger.info(f"[OK] Complete pipeline finished in {total_time:.2f} seconds")
            logger.info(f"[OK] Skill list saved to {skills_path}")

            return index, processed_skills
    except Exception as e:
        logger.error(f"Error in optimized update: {str(e)}")
        return None, []

def query_similar_skills(skill_query, index, skill_list, top_k=5):
    try:
        logger.info(f"Querying: {skill_query}")

        description = generate_single_description(skill_query)
        query_embedding, _ = generate_embeddings_optimized([description])

        if query_embedding.size == 0:
            logger.error("Failed to generate query embedding")
            return None, None, None

        faiss.normalize_L2(query_embedding)
        distances, indices = index.search(query_embedding, min(top_k, index.ntotal))

        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(skill_list):
                results.append({
                    'skill': skill_list[idx],
                    'similarity': float(distance),
                    'rank': i + 1
                })

        return distances, indices, results
    except Exception as e:
        logger.error(f"Error in query: {str(e)}")
        return None, None, None

if __name__ == '__main__':
    logger.info("=== Optimized Embeddings Test ===")

    try:
        if not check_ollama_availability():
            logger.error("Ollama not available")
            exit(1)

        with app.app_context():
            start_time = time.time()
            index, skills = update_embeddings_optimized()
            end_time = time.time()

            logger.info(f"Total processing time: {end_time - start_time:.2f} seconds")

            if index and skills:
                logger.info("[OK] Pipeline successful!")

                test_skill = "Python"
                distances, indices, results = query_similar_skills(test_skill, index, skills, top_k=3)

                if results:
                    logger.info(f"[OK] Query test successful! Similar to '{test_skill}':")
                    for result in results:
                        logger.info(f"  {result['rank']}. {result['skill']} ({result['similarity']:.4f})")
                else:
                    logger.error("Query test failed")
            else:
                logger.error("Pipeline failed")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

    logger.info("=== Test Complete ===")
