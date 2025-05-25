from flask import Blueprint, request, jsonify, render_template
import tempfile
import subprocess
import os
import graphviz
from sqlalchemy import create_engine, text, inspect
import base64

# Create blueprint
diagram = Blueprint('diagram', __name__)

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

    temp_file = None
    output_dir = None
    db_path = None
    output_path = None

    try:
        if diagram_type == 'uml':
            print("Generating UML diagram using PlantUML")

            def generate_plantuml_from_python(code_str):
                import ast
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

            with tempfile.NamedTemporaryFile(suffix='.puml', delete=False, mode='w', encoding='utf-8') as f:
                f.write(plantuml_code)
                temp_file = f.name

            output_dir = tempfile.mkdtemp()

            plantuml_jar_path = os.path.join(os.path.dirname(__file__), 'plantuml.jar')
            result = subprocess.run(
                ['java', '-jar', plantuml_jar_path, '-tpng', '-o', output_dir, temp_file],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                raise Exception(f"PlantUML failed: {result.stderr}")

            # Correctly find the generated PNG file (PlantUML names it after input file)
            png_files = [f for f in os.listdir(output_dir) if f.endswith('.png')]

            if png_files:
                output_path = os.path.join(output_dir, png_files[0])  # get first png file
                with open(output_path, 'rb') as f:
                    data = f.read()
                return jsonify({
                    'success': True,
                    'diagram': base64.b64encode(data).decode('utf-8'),
                    'type': 'uml'
                })
            else:
                files = os.listdir(output_dir)
                return jsonify({'error': f'No UML output. Files: {files}'}), 500

        elif diagram_type == 'erd':
            db_path = tempfile.mktemp(suffix='.db')
            engine = create_engine(f'sqlite:///{db_path}')

            raw_conn = engine.raw_connection()
            try:
                cursor = raw_conn.cursor()
                cursor.executescript(code)
                raw_conn.commit()
            finally:
                raw_conn.close()

            dot = graphviz.Digraph(comment='Database Schema')
            dot.attr(rankdir='LR')
            dot.attr('node', shape='plaintext')

            inspector = inspect(engine)
            tables = inspector.get_table_names()
            if not tables:
                return jsonify({'error': 'No tables found in SQL'}), 400

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
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
            if output_dir and os.path.exists(output_dir):
                __import__('shutil').rmtree(output_dir)
            if db_path and os.path.exists(db_path):
                os.unlink(db_path)
            if output_path and os.path.exists(f'{output_path}.png'):
                os.unlink(f'{output_path}.png')
        except Exception as cleanup_err:
            print(f'Cleanup error: {cleanup_err}')
