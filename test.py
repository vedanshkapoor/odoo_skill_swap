import requests

response = requests.post(
    'http://localhost:11434/api/embeddings',
    json={
        "model": "nomic-embed-text",
        "prompt": "Ollama is working great!"
    }
)

embedding = response.json()["embedding"]
print(f"Embedding length: {len(embedding)}")
print(f"First 5 values: {embedding[:5]}")
