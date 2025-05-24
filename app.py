from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
import os
from dotenv import load_dotenv
import base64
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Create Flask app with explicit static folder
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Get API keys from environment variables
API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Optional GitHub token for higher rate limits

if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

ROLE_INSTRUCTIONS = {
    "frontend": (
        "You are an expert Frontend Developer. "
        "Analyze the following code or question, suggest improvements, and point out any issues in frontend development. "
        "Focus only on frontend concerns like UI, UX, performance, rendering, and frameworks like React, HTML, CSS, etc.\n\n"
    ),
    "backend": (
        "You are an expert Backend Developer. "
        "Analyze the following code or question, suggest improvements, and point out any issues in backend logic, database queries, APIs, scalability, etc.\n\n"
    ),
    "non-technical": (
        "You are a friendly assistant who explains technical concepts in simple, easy-to-understand language. "
        "Avoid technical jargon and explain ideas as if speaking to someone without a tech background.\n\n"
    )
}

def call_gemini_api(role, user_input):
    full_prompt = ROLE_INSTRUCTIONS[role] + user_input

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": full_prompt}]
            }
        ]
    }

    try:
        response = requests.post(
            URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=30
        )
        response.raise_for_status()
        reply = response.json()
        return reply['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.Timeout:
        return "Error: Request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"Error processing response: {str(e)}"

def get_github_headers():
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers

def get_repo_contents(owner, repo, path=''):
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    response = requests.get(url, headers=get_github_headers())
    response.raise_for_status()
    return response.json()

def get_repo_languages(owner, repo):
    url = f'https://api.github.com/repos/{owner}/{repo}/languages'
    response = requests.get(url, headers=get_github_headers())
    response.raise_for_status()
    return response.json()

def format_directory_structure(contents, prefix='', owner=None, repo=None):
    structure = []
    for item in contents:
        if item['type'] == 'dir':
            structure.append(f"{prefix}📁 {item['name']}/")
            try:
                # Use the original owner and repo for subdirectories
                sub_contents = get_repo_contents(owner, repo, item['path'])
                structure.extend(format_directory_structure(sub_contents, prefix + '  ', owner, repo))
            except Exception as e:
                structure.append(f"{prefix}  (Error accessing directory: {str(e)})")
        else:
            structure.append(f"{prefix}📄 {item['name']}")
    return structure

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    role = data.get('role')
    user_input = data.get('input')

    if not role or role not in ROLE_INSTRUCTIONS:
        return jsonify({"error": "Invalid role"}), 400
    
    if not user_input:
        return jsonify({"error": "Empty input"}), 400

    result = call_gemini_api(role, user_input)
    return jsonify({"response": result})

@app.route('/api/analyze-repo', methods=['POST'])
def analyze_repo():
    data = request.json
    owner = data.get('owner')
    repo = data.get('repo')

    if not owner or not repo:
        return jsonify({"error": "Missing owner or repository name"}), 400

    try:
        # Get repository contents
        contents = get_repo_contents(owner, repo)
        structure = format_directory_structure(contents, owner=owner, repo=repo)

        # Get language statistics
        languages = get_repo_languages(owner, repo)
        if not languages:
            return jsonify({"error": "No language data available for this repository"}), 404
            
        total_bytes = sum(languages.values())
        languages = {lang: (bytes/total_bytes)*100 for lang, bytes in languages.items()}

        return jsonify({
            "structure": "\n".join(structure),
            "languages": languages
        })
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": f"Repository not found: {owner}/{repo}"}), 404
        elif e.response.status_code == 403:
            return jsonify({"error": "Rate limit exceeded. Please try again later or use a GitHub token."}), 403
        else:
            return jsonify({"error": f"GitHub API error: {str(e)}"}), e.response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error connecting to GitHub: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error analyzing repository: {str(e)}"}), 500

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/repo-analyzer')
def repo_analyzer():
    return send_from_directory(app.static_folder, 'repo_analyzer.html')

if __name__ == '__main__':
    app.run(debug=True) 