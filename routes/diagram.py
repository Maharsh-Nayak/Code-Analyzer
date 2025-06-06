from flask import Blueprint, request, jsonify, render_template
import tempfile
import os
import base64
import ast
from sqlalchemy import create_engine, inspect
from utils.feedback_learner import FeedbackLearner
from plantuml import PlantUML

# Create blueprint
diagram = Blueprint('diagram', __name__)
feedback_learner = FeedbackLearner()

@diagram.route('/')
def diagram_page():
    return render_template('diagram.html')

@diagram.route('/generate_diagram', methods=['POST'])
def generate_diagram():
    code = request.json.get('code', '')
    diagram_type = request.json.get('type', 'uml')  # 'uml' or 'erd'

    if not code:
        return jsonify({'error': 'No code provided'}), 400

    try:
        if diagram_type == 'uml':
            # === UML Generation with PlantUML ===
            def generate_uml(code_str):
                tree = ast.parse(code_str)
                classes = {}
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        base_classes = [b.id for b in node.bases if isinstance(b, ast.Name)]
                        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                        classes[node.name] = {'bases': base_classes, 'methods': methods}

                lines = ["@startuml", "skinparam classAttributeIconSize 0"]
                for cls, data in classes.items():
                    lines.append(f"class {cls} {{")
                    for method in data["methods"]:
                        lines.append(f"  + {method}()")
                    lines.append("}")
                for cls, data in classes.items():
                    for base in data["bases"]:
                        lines.append(f"{base} <|-- {cls}")
                lines.append("@enduml")
                return "\n".join(lines)

            plantuml_code = generate_uml(code)

        elif diagram_type == 'erd':
            # === ERD Generation with SQL + PlantUML ===
            db_path = tempfile.mktemp(suffix='.db')
            engine = create_engine(f'sqlite:///{db_path}')

            # Use raw connection to execute multiple SQL statements
            raw_conn = engine.raw_connection()
            try:
                cursor = raw_conn.cursor()
                cursor.executescript(code)
                raw_conn.commit()
            finally:
                raw_conn.close()

            inspector = inspect(engine)
            tables = inspector.get_table_names()

            lines = ["@startuml", "hide circle", "skinparam linetype ortho"]
            for table in tables:
                lines.append(f"entity {table} {{")
                for column in inspector.get_columns(table):
                    name = column['name']
                    coltype = str(column['type'])
                    lines.append(f"  {name} : {coltype}")
                lines.append("}")
            for table in tables:
                for fk in inspector.get_foreign_keys(table):
                    if fk['referred_table']:
                        lines.append(f"{fk['referred_table']} ||--o{{ {table} : FK")
            lines.append("@enduml")

            plantuml_code = "\n".join(lines)
            engine.dispose()
            os.unlink(db_path)

        else:
            return jsonify({'error': 'Unsupported diagram type'}), 400

        # Send PlantUML code to public PlantUML server
        server = PlantUML(url='http://www.plantuml.com/plantuml/img/')
        image_data = server.processes(plantuml_code)

        return jsonify({
            'success': True,
            'diagram': base64.b64encode(image_data).decode('utf-8'),
            'type': diagram_type
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@diagram.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    rating = data.get('rating')
    feedback_text = data.get('feedback_text')
    additional_data = data.get('additional_data', {})

    if not all([rating, feedback_text]):
        return jsonify({"error": "Missing required feedback fields"}), 400
    try:
        rating = int(rating)
        if not 1 <= rating <= 5:
            raise ValueError
    except ValueError:
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400

    feedback_learner.save_feedback(
        feedback_type='diagram',
        rating=rating,
        feedback_text=feedback_text,
        additional_data=additional_data
    )
    return jsonify({"message": "Feedback saved successfully"})
