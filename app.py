from flask import Flask, send_from_directory
from routes.repo_analysis import repo_analysis

app = Flask(__name__, static_folder='static')
app.register_blueprint(repo_analysis, url_prefix='/repo-analyzer')

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

if __name__ == '__main__':
    app.run(debug=True) 