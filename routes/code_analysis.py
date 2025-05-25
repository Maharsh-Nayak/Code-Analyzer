from flask import Blueprint, request, jsonify, send_from_directory, session
import requests
import json
import os
from dotenv import load_dotenv
from utils.feedback_learner import FeedbackLearner

# Load environment variables
load_dotenv()

# Create blueprint
code_analysis = Blueprint('code_analysis', __name__, static_folder='static', static_url_path='/static')

# Initialize feedback learner
feedback_learner = FeedbackLearner()

# Get API key from environment variable
API_KEY = "AIzaSyBpSNOx_59sZVEe935VoI8iaA3zlnpQ9_I"
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

BASE_ROLE_INSTRUCTIONS = {
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

def get_role_instructions(role):
    base_instructions = BASE_ROLE_INSTRUCTIONS.get(role, "")
    return feedback_learner.update_instructions(base_instructions, role)

def call_gemini_api(role, user_input):
    # Get role-specific instructions with feedback improvements
    role_instructions = get_role_instructions(role)
    full_prompt = role_instructions + user_input

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

@code_analysis.route('/')
def index():
    return send_from_directory('static', 'index.html')

@code_analysis.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    role = data.get('role')
    user_input = data.get('input')
    skip_feedback = data.get('skip_feedback', False)

    if not role or role not in BASE_ROLE_INSTRUCTIONS:
        return jsonify({"error": "Invalid role"}), 400
    
    if not user_input:
        return jsonify({"error": "Empty input"}), 400

    result = call_gemini_api(role, user_input)
    
    # Get role improvements for context
    role_improvements = feedback_learner.get_role_improvements(role)
    
    # Add feedback requirement to response only if not skipped
    response = {
        "response": result,
        "requires_feedback": not skip_feedback,
        "feedback_type": "code_analysis",
        "feedback_context": {
            "role": role,
            "input_length": len(user_input),
            "improvements": role_improvements
        }
    }
    
    return jsonify(response) 