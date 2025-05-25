from flask import Blueprint, request, jsonify, send_from_directory
import requests
import json
import os
from dotenv import load_dotenv
import markdown
import urllib.parse
from utils.codebase_analyzer import (
    get_enhanced_codebase_map_and_perspectives,
    generate_detailed_perspective_analysis_report,
    consolidate_analysis_report
)
from utils.gemini_client import get_gemini_client

from utils.feedback_learner import FeedbackLearner

# Load environment variables
load_dotenv()

# Create blueprint
code_analysis = Blueprint('code_analysis', __name__)

# Initialize feedback learner
feedback_learner = FeedbackLearner()

# Get API key from environment variable
API_KEY = os.getenv("GEMINI_API_KEY")
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

def extract_query(summary_text: str) -> str:
    """Pick the first 5 words from the summary as a search query."""
    words = summary_text.split()
    return " ".join(words[:5]) if len(words) >= 5 else summary_text
def retrieve_stackoverflow_docs(query: str) -> str:
    # URL encode query
    q = urllib.parse.quote(query)
    url = (
        f"https://api.stackexchange.com/2.3/search/advanced?"
        f"order=desc&sort=relevance&q={q}&site=stackoverflow&pagesize=3&filter=!9_bDDxJY5"
    )
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        items = r.json().get('items', [])
        if not items:
            return ""
        # Extract title and snippet from top 3 questions
        snippets = []
        for item in items:
            title = item.get('title', '')
            # You can also fetch answers with another API call if needed
            snippet = f"Question: {title}"
            snippets.append(snippet)
        return "\n\n".join(snippets)
    except Exception:
        return ""
def retrieve_external_docs(query: str) -> str:
    # Retrieve from Wikipedia as fallback
    wiki_text = retrieve_wikipedia_docs(query)

    # Retrieve from Stack Overflow
    so_text = retrieve_stackoverflow_docs(query)

    # Combine both with prioritization or simple concatenation
    combined_text = "\n\n---\n\n".join(filter(None, [so_text, wiki_text]))
    return combined_text

def retrieve_wikipedia_docs(query: str) -> str:
    title = urllib.parse.quote(query.title())
    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    try:
        r = requests.get(wiki_url, timeout=5)
        r.raise_for_status()
        return r.json().get("extract", "")
    except Exception:
        return ""

def apply_rag(summary_md: str) -> str:
    """
    Given the initial Markdown summary, retrieve external docs 
    and ask Gemini to fuse them into an enhanced summary.
    """
    query = extract_query(summary_md)
    external = retrieve_external_docs(query)
    rag_prompt = (
        "You are a senior developer. Improve the following code summary by "
        "integrating external documentation or best practices. "
        "Keep the result in Markdown format.\n\n"
        "### Original Summary\n"
        f"{summary_md}\n\n"
        "### External Context\n"
        f"{external}\n\n"
        "### Enhanced Summary:"
    )
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": rag_prompt}]}
        ]
    }
    resp = requests.post(
        URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=30
    )
    try:
        resp.raise_for_status()
        reply = resp.json()
        return reply['candidates'][0]['content']['parts'][0]['text']
    except Exception:
        # Fall back to the original summary if RAG fails
        return summary_md

def call_gemini_api(role: str, user_input: str, use_rag: bool = False) -> str:
    """
    Call Gemini for an initial summary, then optionally
    pass that summary through the RAG layer if use_rag is True.
    """
    base_instructions = ROLE_INSTRUCTIONS[role]
    improved_instructions = feedback_learner.update_instructions(base_instructions, role)

    full_prompt = (
        improved_instructions
        + " Please format your response using Markdown. "
        + "Use **bold**, # headings, bullet points, and emojis where appropriate.\n\n"
        + user_input
    )
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": full_prompt}]}
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
        raw_markdown = reply['candidates'][0]['content']['parts'][0]['text']

        # If RAG requested, apply enhancement
        final_markdown = apply_rag(raw_markdown) if use_rag else raw_markdown

        # Convert final Markdown to HTML
        html_response = markdown.markdown(
            final_markdown,
            extensions=['fenced_code', 'codehilite', 'nl2br']
        )
        return html_response

    except requests.exceptions.Timeout:
        return "Error: Request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"Error processing response: {str(e)}"

@code_analysis.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@code_analysis.route('code_analysis/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    role = data.get('role')
    user_input = data.get('input')
    use_rag = bool(data.get('use_rag', False))

    if not role or role not in ROLE_INSTRUCTIONS:
        return jsonify({"error": f"Invalid role '{role}'. Must be one of {list(ROLE_INSTRUCTIONS.keys())}."}), 400
    if not user_input:
        return jsonify({"error": "Empty input"}), 400

    result_html = call_gemini_api(role, user_input, use_rag)
    return jsonify({"response": result_html})

@code_analysis.route('code_analysis/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    role = data.get('role')
    rating = data.get('rating')
    feedback_text = data.get('feedback_text')

    if not all([role, rating, feedback_text]):
        return jsonify({"error": "Missing required feedback fields"}), 400
    try:
        rating = int(rating)
        if not 1 <= rating <= 5:
            raise ValueError
    except ValueError:
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400

    feedback_learner.save_feedback(
        feedback_type='code_analysis',
        rating=rating,
        feedback_text=feedback_text,
        additional_data={'role': role}
    )
    return jsonify({"message": "Feedback saved successfully"})

@code_analysis.route('/analyze', methods=['POST'])
def analyze_codebase():
    try:
        # Get the repository path from the request
        data = request.get_json()
        repo_path = data.get('repo_path')
        
        if not repo_path or not os.path.exists(repo_path):
            return jsonify({
                'error': 'Invalid repository path'
            }), 400

        # Initialize Gemini client
        gemini_client = get_gemini_client()

        # Step 1: Get initial codebase map and perspectives
        codebase_perspectives_json = get_enhanced_codebase_map_and_perspectives(
            repo_path,
            gemini_client
        )

        # Step 2: Generate detailed analysis for each perspective
        perspective_reports = generate_detailed_perspective_analysis_report(
            repo_path,
            codebase_perspectives_json,
            gemini_client
        )

        # Step 3: Consolidate the final report
        final_report = consolidate_analysis_report(
            codebase_perspectives_json,
            perspective_reports
        )

        return jsonify(final_report)

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500
