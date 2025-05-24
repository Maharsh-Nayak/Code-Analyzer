from flask import Blueprint, request, jsonify, send_from_directory
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create blueprint
repo_analysis = Blueprint('repo_analysis', __name__)

# Get GitHub token from environment variable
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Optional GitHub token for higher rate limits

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

@repo_analysis.route('/')
def repo_analyzer():
    return send_from_directory('static', 'repo_analyzer.html')

@repo_analysis.route('/api/analyze-repo', methods=['POST'])
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