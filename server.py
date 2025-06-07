from flask import Flask, send_from_directory
from routes.code_analysis import code_analysis
from routes.repo_analysis import repo_analysis
from routes.diagram import diagram
from routes.feedback import feedback
import os
import os
from flask import request, redirect, render_template, session, url_for
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, 
    static_folder='static',
    static_url_path='/static')
app.secret_key = os.urandom(24)

# Temporary user storage (replace with database in production)
users = {}

# Register blueprints
app.register_blueprint(code_analysis, url_prefix='/code-analyzer')
app.register_blueprint(repo_analysis, url_prefix='/repo-analyzer')
app.register_blueprint(diagram, url_prefix='/diagram-generator')
app.register_blueprint(feedback, url_prefix='/feedback')
app.register_blueprint(about,url_prefix='/about')

@app.route('/')
def home():
    return send_from_directory('templates', 'index.html')

def handler(environ, start_response):
    return app(environ, start_response)

# if __name__ == '__main__':
#     app.run(debug=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
