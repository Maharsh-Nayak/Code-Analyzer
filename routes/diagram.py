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
    print("Received diagram generation request")  # Log request
    code = request.json.get('code', '')
    diagram_type = request.json.get('type', 'uml')  # 'uml' or 'erd'
    
    print(f"Diagram type: {diagram_type}")  # Log diagram type
    print(f"Code length: {len(code)} characters")  # Log code length
    
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    temp_file = None
    output_dir = None
    db_path = None
    output_path = None
    
    try:
        if diagram_type == 'uml':
            print("Generating UML diagram")  # Log UML generation start
            # Create a temporary Python file
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w', encoding='utf-8') as f:
                f.write(code)
                temp_file = f.name
                print(f"Created temporary file: {temp_file}")  # Log temp file creation
            
            # Generate UML diagram using pyreverse
            output_dir = tempfile.mkdtemp()
            print(f"Created output directory: {output_dir}")
            try:
                print("Running Pyreverse")  # Log before running Pyreverse
                # Run pyreverse using subprocess
                result = subprocess.run(
                    ['pyreverse', '-o', 'png', '-d', output_dir, '-p', 'classes', temp_file],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"Pyreverse error: {result.stderr}")
                    raise Exception(f"Pyreverse failed: {result.stderr}")
                
                print("Pyreverse completed")  # Log after Pyreverse
                
                # Read the generated diagram
                diagram_path = os.path.join(output_dir, 'classes_classes.png')  # Updated filename
                print(f"Looking for diagram at: {diagram_path}")  # Log diagram path
                if os.path.exists(diagram_path):
                    print("Diagram file found")  # Log success
                    with open(diagram_path, 'rb') as f:
                        diagram_data = f.read()
                    return jsonify({
                        'success': True,
                        'diagram': base64.b64encode(diagram_data).decode('utf-8'),
                        'type': 'uml'
                    })
                else:
                    # Check if any files were generated
                    generated_files = os.listdir(output_dir)
                    error_msg = f'Failed to generate UML diagram - no output file created. Generated files: {generated_files}'
                    print(error_msg)  # Log the error
                    return jsonify({'error': error_msg}), 500
            except Exception as e:
                error_msg = f'Failed to generate UML diagram: {str(e)}'
                print(error_msg)  # Log the error
                return jsonify({'error': error_msg}), 500
                
        elif diagram_type == 'erd':
            # Create a temporary SQLite database
            db_path = tempfile.mktemp(suffix='.db')
            engine = create_engine(f'sqlite:///{db_path}')
            
            try:
                # Execute the SQL to create tables
                with engine.connect() as conn:
                    conn.execute(text(code))
                    conn.commit()
                
                # Create ERD using graphviz
                dot = graphviz.Digraph(comment='Database Schema')
                dot.attr(rankdir='LR')
                
                # Get table information
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                if not tables:
                    return jsonify({'error': 'No tables found in the provided SQL'}), 400
                
                for table_name in tables:
                    # Create a subgraph for each table
                    with dot.subgraph(name=f'cluster_{table_name}') as s:
                        s.attr(label=table_name)
                        # Get columns
                        columns = inspector.get_columns(table_name)
                        for column in columns:
                            # Format column info
                            col_info = f"{column['name']}\n{column['type']}"
                            if column.get('primary_key'):
                                col_info += " (PK)"
                            if column.get('nullable') is False:
                                col_info += " NOT NULL"
                            s.node(f"{table_name}_{column['name']}", col_info)
                    
                    # Get foreign keys
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    for fk in foreign_keys:
                        # Add edge for foreign key relationship
                        dot.edge(
                            f"{table_name}_{fk['constrained_columns'][0]}",
                            f"{fk['referred_table']}_{fk['referred_columns'][0]}",
                            label="FK"
                        )
                
                # Save the diagram
                output_path = tempfile.mktemp(suffix='.png')
                dot.render(output_path, format='png', cleanup=True)
                
                # Read the generated diagram
                with open(f'{output_path}.png', 'rb') as f:
                    diagram_data = f.read()
                
                return jsonify({
                    'success': True,
                    'diagram': base64.b64encode(diagram_data).decode('utf-8'),
                    'type': 'erd'
                })
            except Exception as e:
                error_msg = f'Failed to generate ERD diagram: {str(e)}'
                print(error_msg)  # Log the error
                return jsonify({'error': error_msg}), 500
            
    except Exception as e:
        error_msg = f'Unexpected error during diagram generation: {str(e)}'
        print(error_msg)  # Log the error
        return jsonify({'error': error_msg}), 500
    finally:
        # Cleanup temporary files
        try:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
            if output_dir and os.path.exists(output_dir):
                import shutil
                shutil.rmtree(output_dir)
            if db_path and os.path.exists(db_path):
                os.unlink(db_path)
            if output_path:
                if os.path.exists(f'{output_path}.png'):
                    os.unlink(f'{output_path}.png')
                if os.path.exists(output_path):
                    os.unlink(output_path)
        except Exception as e:
            print(f'Error during cleanup: {str(e)}')  # Log cleanup errors 