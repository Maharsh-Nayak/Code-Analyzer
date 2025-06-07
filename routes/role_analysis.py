import os
import json
from typing import Dict, List, Optional
import requests
from pathlib import Path
import logging

def get_initial_codebase_overview_from_api(repo_path: str, gemini_client) -> Dict:
    """Get initial overview of the codebase using Gemini."""
    # Get directory structure
    structure = []
    for root, dirs, files in os.walk(repo_path):
        level = root.replace(repo_path, '').count(os.sep)
        indent = ' ' * 4 * level
        structure.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            structure.append(f"{sub_indent}{f}")
    
    # Read key configuration files
    config_files = {
        'README.md': 'Project documentation and overview',
        'package.json': 'Node.js project configuration',
        'requirements.txt': 'Python dependencies',
        'pom.xml': 'Maven project configuration',
        'build.gradle': 'Gradle project configuration',
        'Gemfile': 'Ruby dependencies',
        'composer.json': 'PHP dependencies',
        'Dockerfile': 'Container configuration',
        '.env.example': 'Environment configuration template',
        'docker-compose.yml': 'Multi-container configuration'
    }
    
    file_contents = {}
    for filename, description in config_files.items():
        file_path = os.path.join(repo_path, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    file_contents[filename] = {
                        'content': content,
                        'description': description
                    }
            except Exception as e:
                print(f"Error reading {filename}: {str(e)}")
    
    # Prepare prompt for Gemini
    prompt = f"""Analyze this codebase structure and configuration files to provide a comprehensive overview:

Directory Structure:
{chr(10).join(structure)}

Configuration Files:
{json.dumps(file_contents, indent=2)}

Please provide a detailed analysis in the following JSON format:
{{
    "primary_languages": ["List of main programming languages used"],
    "frameworks": ["List of detected frameworks"],
    "project_type": "Type of project (e.g., web app, mobile app, library)",
    "key_directories": [
        {{
            "path": "directory path",
            "type": "frontend/backend/database/etc",
            "description": "purpose of this directory"
        }}
    ],
    "build_tools": ["List of detected build tools"],
    "deployment_info": {{
        "type": "How the project is deployed",
        "containerization": "Container setup if any",
        "environment": "Environment configuration"
    }},
    "project_summary": "Brief description of the project's purpose"
}}

Focus on providing accurate, well-reasoned insights based on the available information."""
    
    # Get analysis from Gemini
    try:
        response = gemini_client.generate_text_from_gemini(prompt)
        print("[Gemini Raw Response]:", response)
        logging.info(f"[Gemini Raw Response]: {response}")
        if response.strip().startswith('```'):
            response = response.strip().lstrip('`')
            if response.lower().startswith('json'):
                response = response[4:]
            response = response.rstrip('`')
        response = response.strip()
        try:
            return json.loads(response)
        except Exception as parse_err:
            print(f"[Gemini JSON Parse Error]: {parse_err}")
            logging.error(f"[Gemini JSON Parse Error]: {parse_err}")
            return {
                "error": "Failed to parse Gemini response as JSON",
                "details": str(parse_err),
                "raw_response": response
            }
    except Exception as e:
        print(f"[Gemini API Error]: {str(e)}")
        logging.error(f"[Gemini API Error]: {str(e)}")
        return {
            "error": "Failed to analyze codebase",
            "details": str(e)
        }

def select_relevant_files(repo_path: str, overview_json: Dict, role: str) -> List[Dict]:
    """Select relevant files based on role and overview."""
    relevant_files = []
    
    # Map roles to directory types and file patterns
    role_patterns = {
        "frontend": {
            "dir_types": ["frontend", "client", "web", "ui", "src", "app", "components", "pages", "views", "public", "static"],
            "file_patterns": [".js", ".jsx", ".ts", ".tsx", ".vue", ".html", ".css", ".scss", ".sass", ".less", ".styl", ".json", ".svg", ".png", ".jpg", ".gif"],
            "config_files": ["package.json", "webpack.config.js", "vite.config.js", "next.config.js", "angular.json", "tsconfig.json"]
        },
        "backend": {
            "dir_types": ["backend", "server", "api", "src", "app", "lib", "services", "controllers", "routes", "middleware", "utils"],
            "file_patterns": [".py", ".java", ".go", ".rb", ".php", ".js", ".ts", ".cs", ".rs", ".swift", ".kt"],
            "config_files": ["requirements.txt", "pom.xml", "build.gradle", "package.json", "composer.json", "Gemfile", "go.mod", "Cargo.toml"]
        },
        "data": {
            "dir_types": ["database", "models", "schema", "migrations", "data", "db", "sql", "mongo", "redis", "cache"],
            "file_patterns": [".sql", ".py", ".js", ".ts", ".rb", ".php", ".json", ".yaml", ".yml", ".xml", ".csv"],
            "config_files": ["schema.prisma", "sequelize.config.js", "typeorm.config.ts", "database.yml", "db.config.js"]
        }
    }
    
    # Get patterns for the role
    patterns = role_patterns.get(role.lower(), {})
    if not patterns:
        return []
    
    # First, check for configuration files
    for config_file in patterns.get("config_files", []):
        config_path = os.path.join(repo_path, config_file)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    relevant_files.append({
                        "path": config_file,
                        "content": content,
                        "type": "config"
                    })
            except Exception as e:
                print(f"Error reading config file {config_file}: {str(e)}")
    
    # Find relevant directories from overview
    relevant_dirs = [
        dir_info["path"] for dir_info in overview_json.get("key_directories", [])
        if dir_info["type"] in patterns["dir_types"]
    ]
    
    # If no specific directories found, use common project directories
    if not relevant_dirs:
        relevant_dirs = [d for d in patterns["dir_types"] if os.path.exists(os.path.join(repo_path, d))]
    
    # If still no directories found, use the entire repo
    if not relevant_dirs:
        relevant_dirs = [repo_path]
    
    # Find relevant files
    for directory in relevant_dirs:
        dir_path = os.path.join(repo_path, directory)
        if not os.path.exists(dir_path):
            continue
            
        for root, _, files in os.walk(dir_path):
            for file in files:
                # Skip node_modules, .git, and other common non-relevant directories
                if any(skip_dir in root for skip_dir in ['node_modules', '.git', 'dist', 'build', 'coverage']):
                    continue
                    
                if any(file.endswith(pattern) for pattern in patterns["file_patterns"]):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            relevant_files.append({
                                "path": os.path.relpath(file_path, repo_path),
                                "content": content,
                                "type": "code"
                            })
                    except Exception as e:
                        print(f"Error reading {file_path}: {str(e)}")
    
    return relevant_files

def generate_role_specific_prompt(role: str, overview_json: Dict, relevant_files: List[Dict]) -> str:
    """Generate a role-specific prompt for Gemini."""
    # Group files by type
    config_files = [f for f in relevant_files if f.get("type") == "config"]
    code_files = [f for f in relevant_files if f.get("type") == "code"]
    
    # Create a summary of the files
    file_summary = {
        "config_files": {f["path"]: f["content"] for f in config_files},
        "code_files": {f["path"]: f["content"] for f in code_files}
    }
    
    role_prompts = {
        "frontend": """You are an expert Frontend Developer analyzing a codebase. Based on the project overview and the following frontend files:

Project Overview:
{}

Frontend Files:
{}

Please provide a detailed analysis in the following JSON format:
{{
    "key_ui_components": [
        {{
            "name": "Component name",
            "responsibility": "Main purpose",
            "user_interactions": "How users interact with it",
            "location": "File path"
        }}
    ],
    "consumed_api_endpoints": [
        {{
            "path": "API endpoint path",
            "purpose": "What it's used for",
            "data_handling": "How the data is used",
            "location": "File path"
        }}
    ],
    "data_flow_example": "Description of a key feature's data flow",
    "state_management": {{
        "pattern": "State management approach used",
        "key_stores": "Main state stores/contexts",
        "data_flow": "How data flows through the state",
        "location": "File path"
    }},
    "navigation": {{
        "main_routes": "Key navigation paths",
        "routing_pattern": "How routing is implemented",
        "location": "File path"
    }},
    "styling": {{
        "approach": "CSS/styling approach used",
        "frameworks": "CSS frameworks or libraries",
        "theming": "Theme implementation if any",
        "location": "File path"
    }},
    "build_tools": {{
        "bundler": "Bundler used (webpack, vite, etc.)",
        "configuration": "Key build configurations",
        "location": "File path"
    }}
}}""",

        "backend": """You are an expert Backend Developer analyzing a codebase. Based on the project overview and the following backend files:

Project Overview:
{}

Backend Files:
{}

Please provide a detailed analysis in the following JSON format:
{{
    "core_logic": {{
        "main_functionality": "Core business logic",
        "key_services": "Main service components",
        "business_rules": "Important business rules",
        "location": "File path"
    }},
    "api_endpoints": [
        {{
            "path": "Endpoint path",
            "method": "HTTP method",
            "purpose": "What it does",
            "request_format": "Expected request format",
            "response_format": "Response format",
            "location": "File path"
        }}
    ],
    "database": {{
        "interaction_pattern": "How the backend interacts with the database",
        "key_models": "Important data models",
        "query_patterns": "Common database operations",
        "location": "File path"
    }},
    "authentication": {{
        "mechanism": "Auth approach used",
        "key_components": "Main auth components",
        "security_measures": "Security features",
        "location": "File path"
    }},
    "data_processing": {{
        "transformations": "Data processing steps",
        "validation": "Data validation approach",
        "error_handling": "Error handling strategy",
        "location": "File path"
    }},
    "deployment": {{
        "environment": "Deployment environment",
        "configuration": "Deployment configuration",
        "scaling": "Scaling approach if any",
        "location": "File path"
    }}
}}""",

        "data": """You are an expert Data Engineer analyzing a codebase. Based on the project overview and the following data-related files:

Project Overview:
{}

Data Files:
{}

Please provide a detailed analysis in the following JSON format:
{{
    "data_models": [
        {{
            "name": "Model name",
            "purpose": "What it represents",
            "key_fields": "Important fields",
            "relationships": "Relationships with other models",
            "location": "File path"
        }}
    ],
    "database": {{
        "type": "Database technology",
        "schema_pattern": "Schema organization",
        "migration_strategy": "How schema changes are managed",
        "location": "File path"
    }},
    "data_operations": {{
        "common_queries": "Frequent database operations",
        "data_transformations": "ETL or data processing",
        "optimization": "Performance considerations",
        "location": "File path"
    }},
    "data_quality": {{
        "validation": "Data validation approach",
        "constraints": "Data constraints",
        "integrity": "Data integrity measures",
        "location": "File path"
    }},
    "data_flow": {{
        "sources": "Data sources",
        "transformations": "Data transformation steps",
        "destinations": "Data destinations",
        "location": "File path"
    }}
}}""",

        "product": """You are a Product Manager analyzing a codebase. Based on the project overview and the following information:

Project Overview:
{}

Please provide a detailed analysis in the following JSON format:
{{
    "key_features": [
        {{
            "name": "Feature name",
            "purpose": "What it does",
            "user_value": "Value to users",
            "implementation": "How it's implemented"
        }}
    ],
    "problem_solved": "Main problem the application solves",
    "value_proposition": "Core value offered to users",
    "target_audience": {{
        "primary": "Main user group",
        "secondary": "Other user groups",
        "needs": "User needs addressed"
    }},
    "user_journey": {{
        "key_paths": "Main user flows",
        "interaction_points": "Key user interactions",
        "value_delivery": "How value is delivered"
    }},
    "technical_constraints": {{
        "limitations": "Technical limitations",
        "dependencies": "Key technical dependencies",
        "scalability": "Scalability considerations"
    }},
    "future_considerations": {{
        "improvements": "Potential improvements",
        "risks": "Technical risks",
        "opportunities": "Growth opportunities"
    }}
}}"""
    }
    
    # Get the appropriate prompt template
    prompt_template = role_prompts.get(role.lower())
    if not prompt_template:
        return ""
    
    # Format the prompt with the actual data
    return prompt_template.format(
        json.dumps(overview_json, indent=2),
        json.dumps(file_summary, indent=2)
    )

def parse_gemini_response(response: str) -> Dict:
    """Parse Gemini's response into structured JSON."""
    try:
        # Try to parse as JSON directly
        return json.loads(response)
    except json.JSONDecodeError:
        # If not valid JSON, try to extract JSON from the text
        try:
            # Look for JSON-like structure in the text
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except:
            pass
        
        # If all parsing attempts fail, return error
        return {
            "error": "Failed to parse Gemini response",
            "raw_response": response
        }

def parse_stringified_json(obj):
    """Recursively parse stringified JSON objects/arrays in a dict or list, even if deeply nested."""
    import json
    def try_parse(val):
        if isinstance(val, str):
            val_strip = val.strip()
            # Only try to parse if it looks like JSON
            if (val_strip.startswith('{') and val_strip.endswith('}')) or (val_strip.startswith('[') and val_strip.endswith(']')):
                try:
                    parsed = json.loads(val_strip)
                    # Recursively parse the result
                    return try_parse(parsed)
                except Exception:
                    return val
        elif isinstance(val, list):
            return [try_parse(item) for item in val]
        elif isinstance(val, dict):
            return {k: try_parse(v) for k, v in val.items()}
        return val
    return try_parse(obj)

def generate_multi_role_summary_report_from_api(repo_path: str, overview_json: Dict, gemini_client) -> Dict:
    """Generate comprehensive role-specific summaries."""
    roles = ["frontend", "backend", "data", "product"]
    report = {
        "project_overview": overview_json,
        "role_summaries": {}
    }
    
    for role in roles:
        # Select relevant files for this role
        relevant_files = select_relevant_files(repo_path, overview_json, role)
        
        # Generate role-specific prompt
        prompt = generate_role_specific_prompt(role, overview_json, relevant_files)
        if not prompt:
            continue
        
        # Get analysis from Gemini
        try:
            response = gemini_client.generate_text_from_gemini(prompt)
            role_summary = parse_gemini_response(response)
            # Recursively parse stringified JSON in the summary
            role_summary = parse_stringified_json(role_summary)
            report["role_summaries"][f"{role}_summary"] = role_summary
        except Exception as e:
            print(f"Error generating {role} summary: {str(e)}")
            report["role_summaries"][f"{role}_summary"] = {
                "error": f"Failed to generate {role} summary",
                "details": str(e)
            }
    
    return report 
