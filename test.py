import requests
import json

def run_phi3(prompt):
    url = "http://localhost:11434/api/generate"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "phi3",  # You can change to "phi3:medium" or just "phi3"
        "prompt": prompt,
        "stream": False  # Set to True if you want token-by-token streaming
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        result = response.json()
        print("🧠 Prompt:", prompt)
        print("💬 Response:", result.get("response", ""))
    else:
        print("❌ Failed to generate response")
        print(f"Status Code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_prompt = "Explain quantum computing in simple terms."
    run_phi3(test_prompt)
