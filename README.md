# Gemini Code Analyzer Web

A modern web application that uses Google's Gemini AI to analyze code and provide technical explanations. The application supports different roles (frontend, backend, and non-technical) to get specialized responses for your queries.

## Features

- Role-based code analysis (Frontend, Backend, Non-technical)
- Modern, responsive web interface
- Real-time API integration
- Loading indicators and error handling
- Keyboard shortcuts (Ctrl+Enter to submit)
- Mobile-friendly design

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Running the Application

1. Start the Flask development server:
   ```bash
   python app.py
   ```
2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

## Development

The application is built with:
- Backend: Flask (Python)
- Frontend: HTML, CSS (Tailwind CSS), JavaScript
- API: Google Gemini AI

### Project Structure
```
.
├── app.py              # Flask backend
├── requirements.txt    # Python dependencies
├── static/            # Frontend assets
│   ├── index.html     # Main HTML file
│   ├── styles.css     # Custom CSS
│   └── app.js         # Frontend JavaScript
└── .env               # Environment variables (create this)
```

## Requirements

- Python 3.7+
- Internet connection for API access
- Valid Gemini API key

## Security Note

Never commit your API key to version control. Always use environment variables or a secure configuration management system. 