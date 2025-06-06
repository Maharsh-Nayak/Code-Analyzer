from flask import Blueprint, request, jsonify, render_template
import tempfile
import os
import graphviz
from sqlalchemy import create_engine, text, inspect
import base64
from utils.feedback_learner import FeedbackLearner
from plantuml import PlantUML
import ast
import subprocess
from flask import jsonify

# Create blueprint
diagram = Blueprint('diagram', __name__)

# Initialize feedback learner
feedback_learner = FeedbackLearner()

@diagram.route('/')

    
def diagram_page():
    return render_template('diagram.html')

@diagram.route('/generate_diagram', methods=['POST'])
def generate_diagram():
    print("Received diagram generation request")
    code = request.json.get('code', '')
    diagram_type = request.json.get('type', 'uml')  # 'uml' or 'erd'

    print(f"Diagram type: {diagram_type}")
    print(f"Code length: {len(code)} characters")

    if not code:
        return jsonify({'error': 'No code provided'}), 400

    db_path = None
    output_path = None

    try:
        if diagram_type == 'uml':
            print("Generating UML diagram using PlantUML HTTP API")

            def generate_plantuml_from_python(code_str):
                tree = ast.parse(code_str)
                classes = {}

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        base_classes = [base.id for base in node.bases if isinstance(base, ast.Name)]
                        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                        classes[node.name] = {
                            "bases": base_classes,
                            "methods": methods
                        }

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

            plantuml_code = generate_plantuml_from_python(code)

            # Send to public PlantUML server
            server = PlantUML(url='http://www.plantuml.com/plantuml/img/')
            image_data = server.processes(plantuml_code)

            return jsonify({
                'success': True,
                'diagram': base64.b64encode(image_data).decode('utf-8'),
                'type': 'uml'
            })

                elif diagram_type == 'erd':
            print("Generating ERD using ERAlchemy with PlantUML backend")
            db_path = tempfile.mktemp(suffix='.db')
            engine = create_engine(f'sqlite:///{db_path}')

            raw_conn = engine.raw_connection()
            try:
                cursor = raw_conn.cursor()
                cursor.executescript(code)
                raw_conn.commit()
            finally:
                raw_conn.close()

            # Generate PlantUML file using ERAlchemy
            puml_output = tempfile.mktemp(suffix=".puml")
            subprocess.run([
                "eralchemy",
                "-i", f"sqlite:///{db_path}",
                "-o", puml_output,
                "--plantuml"
            ], check=True)

            # Now render the PlantUML using the public PlantUML server
            with open(puml_output, "r") as f:
                puml_code = f.read()

            server = PlantUML(url='http://www.plantuml.com/plantuml/img/')
            image_data = server.processes(puml_code)

            return jsonify({
                'success': True,
                'diagram': base64.b64encode(image_data).decode('utf-8'),
                'type': 'erd'
            })

            for table in tables:
                cols = inspector.get_columns(table)
                label = f'''<
<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
  <TR><TD BGCOLOR="lightblue" COLSPAN="2"><B>{table}</B></TD></TR>
'''
                for c in cols:
                    name, typ = c['name'], str(c['type'])
                    pk = c.get('primary_key', False)
                    nn = not c.get('nullable', True)
                    style = 'BGCOLOR="palegreen"' if pk else ('BGCOLOR="mistyrose"' if nn else '')
                    pk_text = ' PK' if pk else ''
                    nn_text = ' NOT NULL' if nn else ''
                    label += f'<TR><TD ALIGN="LEFT" {style}>{name}{pk_text}</TD><TD ALIGN="LEFT">{typ}{nn_text}</TD></TR>\n'
                label += '</TABLE>>'
                dot.node(table, label=label, _attributes={'labeltype': 'html'})

            for table in tables:
                for fk in inspector.get_foreign_keys(table):
                    src_cols = fk.get('constrained_columns') or []
                    tgt_table = fk.get('referred_table')
                    tgt_cols = fk.get('referred_columns') or []
                    if not tgt_table:
                        continue
                    for src, tgt in zip(src_cols, tgt_cols):
                        dot.edge(table, tgt_table, label=f'FK: {src}→{tgt}', color='blue')

            output_path = tempfile.mktemp(suffix='.png')
            dot.format = 'png'
            dot.render(filename=output_path, cleanup=True)

            with open(f'{output_path}.png', 'rb') as f:
                data = f.read()
            return jsonify({'success': True,
                            'diagram': base64.b64encode(data).decode('utf-8'),
                            'type': 'erd'})

        else:
            return jsonify({'error': 'Unsupported diagram type'}), 400

    except Exception as e:
        print(f'Error during diagram gen: {e}')
        return jsonify({'error': str(e)}), 500

    finally:
        try:
            if db_path and os.path.exists(db_path):
                os.unlink(db_path)
            if output_path and os.path.exists(f'{output_path}.png'):
                os.unlink(f'{output_path}.png')
        except Exception as cleanup_err:
            print(f'Cleanup error: {cleanup_err}')

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
