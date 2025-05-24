import requests
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox
import os
from dotenv import load_dotenv
import threading

# Load environment variables
load_dotenv()

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
            timeout=30  # Add timeout
        )
        response.raise_for_status()  # Raise exception for bad status codes
        reply = response.json()
        return reply['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.Timeout:
        return "Error: Request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"Error processing response: {str(e)}"


def on_submit():
    role = role_var.get()
    user_input = input_text.get("1.0", tk.END).strip()
    if role not in ROLE_INSTRUCTIONS:
        messagebox.showerror("Invalid Role", "Please select a valid role: frontend, backend, or non-technical.")
        return
    if not user_input:
        messagebox.showerror("Empty Input", "Please enter a question or code snippet.")
        return

    # Disable submit button during processing
    submit_btn.config(state=tk.DISABLED)
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, "Processing...\n")

    def process_request():
        try:
            result = call_gemini_api(role, user_input)
            output_text.delete("1.0", tk.END)
            output_text.insert(tk.END, result)
        finally:
            # Re-enable submit button
            submit_btn.config(state=tk.NORMAL)

    # Run API call in a separate thread
    threading.Thread(target=process_request, daemon=True).start()


# Tkinter GUI setup
root = tk.Tk()
root.title("Gemini Code Analyzer")
root.geometry("800x800")  # Set initial window size

# Create main frame with padding
main_frame = tk.Frame(root, padx=20, pady=20)
main_frame.pack(fill=tk.BOTH, expand=True)

# Role selection frame
role_frame = tk.Frame(main_frame)
role_frame.pack(fill=tk.X, pady=(0, 10))

tk.Label(role_frame, text="Select Role:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
role_var = tk.StringVar(value="frontend")
role_menu = tk.OptionMenu(role_frame, role_var, "frontend", "backend", "non-technical")
role_menu.pack(side=tk.LEFT)

# Input frame
input_frame = tk.Frame(main_frame)
input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

tk.Label(input_frame, text="Enter your message or code:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
input_text = scrolledtext.ScrolledText(input_frame, width=80, height=10, wrap=tk.WORD)
input_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

# Button frame
button_frame = tk.Frame(main_frame)
button_frame.pack(fill=tk.X, pady=10)

def clear_input():
    input_text.delete("1.0", tk.END)

def clear_output():
    output_text.delete("1.0", tk.END)

submit_btn = tk.Button(button_frame, text="Submit", command=on_submit, width=15)
submit_btn.pack(side=tk.LEFT, padx=(0, 10))

clear_input_btn = tk.Button(button_frame, text="Clear Input", command=clear_input, width=15)
clear_input_btn.pack(side=tk.LEFT, padx=(0, 10))

clear_output_btn = tk.Button(button_frame, text="Clear Output", command=clear_output, width=15)
clear_output_btn.pack(side=tk.LEFT)

# Output frame
output_frame = tk.Frame(main_frame)
output_frame.pack(fill=tk.BOTH, expand=True)

tk.Label(output_frame, text="Gemini's Response:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
output_text = scrolledtext.ScrolledText(output_frame, width=80, height=15, wrap=tk.WORD)
output_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

# Configure grid weights for resizing
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
main_frame.grid_rowconfigure(2, weight=1)  # Input frame
main_frame.grid_rowconfigure(4, weight=1)  # Output frame
main_frame.grid_columnconfigure(0, weight=1)

root.mainloop()