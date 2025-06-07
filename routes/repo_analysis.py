from flask import Blueprint, request, jsonify, send_from_directory
import requests
import os
import base64

from dotenv import load_dotenv
from typing import Optional
from .role_analysis import (
    get_initial_codebase_overview_from_api,
    generate_multi_role_summary_report_from_api
)
from utils.feedback_learner import FeedbackLearner

# Load environment variables
load_dotenv()

# Create blueprint
repo_analysis = Blueprint('repo_analysis', __name__)

# Initialize feedback learner
feedback_learner = FeedbackLearner()

# Get API keys
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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

def get_file_content(owner, repo, path):
    contents = get_repo_contents(owner, repo, path)
    if contents.get('encoding') == 'base64':
        return base64.b64decode(contents['content']).decode('utf-8')
    return ""

def get_all_code_files(owner, repo, path=''):
    code_files = []
    items = get_repo_contents(owner, repo, path)
    for item in items:
        if item['type'] == 'file':
            if item['name'].endswith(('.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.java', '.go')):
                content = get_file_content(owner, repo, item['path'])
                code_files.append({'path': item['path'], 'content': content})
        elif item['type'] == 'dir':
            code_files.extend(get_all_code_files(owner, repo, item['path']))
    return code_files

def format_directory_structure(contents, prefix='', owner=None, repo=None):
    structure = []
    for item in contents:
        if item['type'] == 'dir':
            structure.append(f"{prefix}📁 {item['name']}/")
            try:
                sub_contents = get_repo_contents(owner, repo, item['path'])
                structure.extend(format_directory_structure(sub_contents, prefix + '  ', owner, repo))
            except Exception as e:
                structure.append(f"{prefix}  (Error accessing directory: {str(e)})")
        else:
            structure.append(f"{prefix}📄 {item['name']}")
    return structure

def get_repo_languages(owner, repo):
    url = f'https://api.github.com/repos/{owner}/{repo}/languages'
    response = requests.get(url, headers=get_github_headers())
    response.raise_for_status()
    return response.json()

class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def generate_text_from_gemini(self, prompt: str) -> str:
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        try:
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            raise

@repo_analysis.route('/')
def repo_analyzer():
    return send_from_directory('templates', 'repo_analyzer.html')

@repo_analysis.route('/repo_analyzer/api/analyze-repo', methods=['POST'])
def analyze_repo():
    data = request.json
    owner = data.get('owner')
    repo = data.get('repo')

    if not owner or not repo:
        return jsonify({"error": "Missing owner or repository name"}), 400

    try:
        gemini_client = GeminiClient(API_KEY)

        code_files = get_all_code_files(owner, repo)
        if not code_files:
            return jsonify({"error": "No valid code files found in repository"}), 400

        # Step 1: Get project overview (safe fallback if string)
        overview_raw = get_initial_codebase_overview_from_api(code_files, gemini_client)

        # Step 2: Safely parse or wrap it
        if isinstance(overview_raw, dict):
            project_overview = overview_raw
        else:
            try:
                import json
                project_overview = json.loads(overview_raw)
            except:
                project_overview = {"description": str(overview_raw).strip()}

        # Step 3: Generate role summaries
        role_summaries = generate_multi_role_summary_report_from_api(code_files, project_overview, gemini_client)

        contents = get_repo_contents(owner, repo)
        structure = format_directory_structure(contents, owner=owner, repo=repo)

        languages = get_repo_languages(owner, repo)
        if not languages:
            return jsonify({"error": "No language data available for this repository"}), 404

        total_bytes = sum(languages.values())
        languages = {lang: (bytes / total_bytes) * 100 for lang, bytes in languages.items()}

        return jsonify({
            "structure": "\n".join(structure),
            "languages": languages,
            "project_overview": project_overview,
            "role_summaries": role_summaries["role_summaries"]
        })

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": f"Repository not found: {owner}/{repo}"}), 404
        elif e.response.status_code == 403:
            return jsonify({"error": "Rate limit exceeded. Please try again later or use a GitHub token."}), 403
        else:
            return jsonify({"error": f"GitHub API error: {str(e)}"}), e.response.status_code
    except Exception as e:
        return jsonify({"error": f"Error analyzing repository: {str(e)}"}), 500

@repo_analysis.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    rating = data.get('rating')
    feedback_text = data.get('feedback_text')
    additional_data = data.get('additional_data', {})

    if not all([rating, feedback_text]):
        return jsonify({"error": "Missing required feedback fields"}), 400
    try:
        rating = int(rating)
        if not 1 <= rating <= 5:
            raise ValueError
    except ValueError:
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400

    feedback_learner.save_feedback(
        feedback_type='repo_analysis',
        rating=rating,
        feedback_text=feedback_text,
        additional_data=additional_data
    )
    return jsonify({"message": "Feedback saved successfully"})
