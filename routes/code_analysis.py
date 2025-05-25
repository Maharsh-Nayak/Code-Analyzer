from flask import Blueprint, request, jsonify, send_from_directory
import requests
import json
import os
import json
from dotenv import load_dotenv
import markdown 
import re

# Load environment variables
load_dotenv()

# Create blueprint
code_analysis = Blueprint('code_analysis', __name__)

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

def call_gemini_api(role, user_input):
    full_prompt = (
        ROLE_INSTRUCTIONS[role]
        + " Please format your response using Markdown. "
        + "Use **bold**, # headings, bullet points, and emojis where appropriate.\n\n"
        + user_input
    )
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
        raw_markdown = reply['candidates'][0]['content']['parts'][0]['text']

        # ✅ Convert Markdown to HTML
        html_response = markdown.markdown(
            raw_markdown,
            extensions=['fenced_code', 'codehilite', 'nl2br']  # Optional: better formatting
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

    if not role or role not in ROLE_INSTRUCTIONS:
        return jsonify({"error": "Invalid role"}), 400
    
    if not user_input:
        return jsonify({"error": "Empty input"}), 400

    result = call_gemini_api(role, user_input)
    return jsonify({"response": result}) 