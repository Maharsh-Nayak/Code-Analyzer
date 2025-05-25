from flask import Flask, send_from_directory
from routes.code_analysis import code_analysis
from routes.repo_analysis import repo_analysis
from routes.diagram import diagram
from routes.feedback import feedback
import os

app = Flask(__name__, 
    static_folder='static',
    static_url_path='/static')

# Register blueprints
app.register_blueprint(code_analysis, url_prefix='/code-analyzer')
app.register_blueprint(repo_analysis, url_prefix='/repo-analyzer')
app.register_blueprint(diagram, url_prefix='/diagram-generator')
app.register_blueprint(feedback, url_prefix='/feedback')

@app.route('/')
def home():
    return send_from_directory('static', 'home.html')

if __name__ == '__main__':
    app.run(debug=True) 