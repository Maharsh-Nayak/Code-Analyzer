from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import requests
import json
import os
from dotenv import load_dotenv
import base64
from urllib.parse import urlparse
from github import Github
import tempfile
import subprocess
from pylint.pyreverse.main import Run
import graphviz
from sqlalchemy import create_engine, MetaData, text, inspect
import sys
from io import StringIO

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

@app.route('/diagram')
def diagram():
    return render_template('diagram.html')

@app.route('/generate_diagram', methods=['POST'])
def generate_diagram():
    print("Received diagram generation request")  # Log request
    code = request.json.get('code', '')
    diagram_type = request.json.get('type', 'uml')  # 'uml' or 'erd'
    
    print(f"Diagram type: {diagram_type}")  # Log diagram type
    print(f"Code length: {len(code)} characters")  # Log code length
    
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    temp_file = None
    output_dir = None
    db_path = None
    output_path = None
    
    try:
        if diagram_type == 'uml':
            print("Generating UML diagram")  # Log UML generation start
            # Create a temporary Python file
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w', encoding='utf-8') as f:
                f.write(code)
                temp_file = f.name
                print(f"Created temporary file: {temp_file}")  # Log temp file creation
            
            # Generate UML diagram using pyreverse
            output_dir = tempfile.mkdtemp()
            print(f"Created output directory: {output_dir}")  # Log output directory
            try:
                print("Running Pyreverse")  # Log before running Pyreverse
                # Run pyreverse using subprocess
                result = subprocess.run(
                    ['pyreverse', '-o', 'png', '-d', output_dir, '-p', 'classes', temp_file],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"Pyreverse error: {result.stderr}")
                    raise Exception(f"Pyreverse failed: {result.stderr}")
                
                print("Pyreverse completed")  # Log after Pyreverse
                
                # Read the generated diagram
                diagram_path = os.path.join(output_dir, 'classes_classes.png')  # Updated filename
                print(f"Looking for diagram at: {diagram_path}")  # Log diagram path
                if os.path.exists(diagram_path):
                    print("Diagram file found")  # Log success
                    with open(diagram_path, 'rb') as f:
                        diagram_data = f.read()
                    return jsonify({
                        'success': True,
                        'diagram': base64.b64encode(diagram_data).decode('utf-8'),
                        'type': 'uml'
                    })
                else:
                    # Check if any files were generated
                    generated_files = os.listdir(output_dir)
                    error_msg = f'Failed to generate UML diagram - no output file created. Generated files: {generated_files}'
                    print(error_msg)  # Log the error
                    return jsonify({'error': error_msg}), 500
            except Exception as e:
                error_msg = f'Failed to generate UML diagram: {str(e)}'
                print(error_msg)  # Log the error
                return jsonify({'error': error_msg}), 500
                
        elif diagram_type == 'erd':
            # Create a temporary SQLite database
            db_path = tempfile.mktemp(suffix='.db')
            engine = create_engine(f'sqlite:///{db_path}')
            
            try:
                # Execute the SQL to create tables
                with engine.connect() as conn:
                    conn.execute(text(code))
                    conn.commit()
                
                # Create ERD using graphviz
                dot = graphviz.Digraph(comment='Database Schema')
                dot.attr(rankdir='LR')
                
                # Get table information
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                if not tables:
                    return jsonify({'error': 'No tables found in the provided SQL'}), 400
                
                for table_name in tables:
                    # Create a subgraph for each table
                    with dot.subgraph(name=f'cluster_{table_name}') as s:
                        s.attr(label=table_name)
                        # Get columns
                        columns = inspector.get_columns(table_name)
                        for column in columns:
                            # Format column info
                            col_info = f"{column['name']}\n{column['type']}"
                            if column.get('primary_key'):
                                col_info += " (PK)"
                            if column.get('nullable') is False:
                                col_info += " NOT NULL"
                            s.node(f"{table_name}_{column['name']}", col_info)
                    
                    # Get foreign keys
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    for fk in foreign_keys:
                        # Add edge for foreign key relationship
                        dot.edge(
                            f"{table_name}_{fk['constrained_columns'][0]}",
                            f"{fk['referred_table']}_{fk['referred_columns'][0]}",
                            label="FK"
                        )
                
                # Save the diagram
                output_path = tempfile.mktemp(suffix='.png')
                dot.render(output_path, format='png', cleanup=True)
                
                # Read the generated diagram
                with open(f'{output_path}.png', 'rb') as f:
                    diagram_data = f.read()
                
                return jsonify({
                    'success': True,
                    'diagram': base64.b64encode(diagram_data).decode('utf-8'),
                    'type': 'erd'
                })
            except Exception as e:
                error_msg = f'Failed to generate ERD diagram: {str(e)}'
                print(error_msg)  # Log the error
                return jsonify({'error': error_msg}), 500
            
    except Exception as e:
        error_msg = f'Unexpected error during diagram generation: {str(e)}'
        print(error_msg)  # Log the error
        return jsonify({'error': error_msg}), 500
    finally:
        # Cleanup temporary files
        try:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
            if output_dir and os.path.exists(output_dir):
                import shutil
                shutil.rmtree(output_dir)
            if db_path and os.path.exists(db_path):
                os.unlink(db_path)
            if output_path:
                if os.path.exists(f'{output_path}.png'):
                    os.unlink(f'{output_path}.png')
                if os.path.exists(output_path):
                    os.unlink(output_path)
        except Exception as e:
            print(f'Error during cleanup: {str(e)}')  # Log cleanup errors

if __name__ == '__main__':
    app.run(debug=True) 