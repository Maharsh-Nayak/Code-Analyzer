import os
import json
import mistune
from typing import Dict, List, Any

def get_enhanced_codebase_map_and_perspectives(repo_path: str, gemini_client) -> Dict[str, Any]:
    """
    Analyzes the codebase to identify major functional perspectives and their characteristics.
    """
    # 1. Gather context: README, config files, directory structure
    readme = read_file_if_exists(os.path.join(repo_path, "README.md"))
    config_files = []
    for fname in ["package.json", "pyproject.toml", "requirements.txt", "Pipfile", "setup.py"]:
        fpath = os.path.join(repo_path, fname)
        if os.path.exists(fpath):
            config_files.append((fname, read_file_if_exists(fpath)))
    dir_structure = get_top_level_directory_structure(repo_path)

    # 2. Build the prompt
    prompt = build_gemini_perspective_prompt(readme, config_files, dir_structure)

    # 3. Call Gemini
    gemini_response = gemini_client.generate_content(prompt)
    
    # 4. Parse JSON from Gemini's response
    try:
        codebase_perspectives_json = json.loads(gemini_response.text)
    except Exception as e:
        raise ValueError(f"Gemini did not return valid JSON: {e}\nResponse: {gemini_response.text}")

    return codebase_perspectives_json

def generate_detailed_perspective_analysis_report(repo_path: str, codebase_perspectives_json: Dict[str, Any], gemini_client) -> Dict[str, Any]:
    """
    Generates detailed analysis for each identified perspective.
    """
    perspective_reports = {}
    
    for perspective in codebase_perspectives_json["identified_perspectives"]:
        files_content = gather_files_for_perspective(repo_path, perspective)
        
        # Select appropriate prompt based on perspective type
        if "Frontend" in perspective["perspective_name"]:
            prompt = build_frontend_ui_layer_prompt(
                codebase_perspectives_json["project_summary"],
                perspective,
                files_content
            )
        elif "Backend" in perspective["perspective_name"]:
            prompt = build_backend_api_layer_prompt(
                codebase_perspectives_json["project_summary"],
                perspective,
                files_content
            )
        else:
            # Generic prompt for other perspectives
            prompt = build_generic_perspective_prompt(
                codebase_perspectives_json["project_summary"],
                perspective,
                files_content
            )

        # Get Gemini's analysis
        gemini_response = gemini_client.generate_content(prompt)
        markdown_output = gemini_response.text

        # Parse markdown to JSON based on perspective type
        if "Frontend" in perspective["perspective_name"]:
            perspective_json = parse_frontend_ui_layer_markdown(markdown_output)
        elif "Backend" in perspective["perspective_name"]:
            perspective_json = parse_backend_api_layer_markdown(markdown_output)
        else:
            perspective_json = parse_generic_markdown(markdown_output)

        perspective_reports[perspective["perspective_name"]] = perspective_json

    return perspective_reports

def consolidate_analysis_report(codebase_perspectives_json: Dict[str, Any], perspective_reports: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combines all perspective analyses into a single, well-structured report.
    """
    return {
        "project_summary": codebase_perspectives_json.get("project_summary", ""),
        "detected_tech_stack": codebase_perspectives_json.get("detected_tech_stack", []),
        "perspectives": perspective_reports
    }

# Helper functions
def read_file_if_exists(path: str) -> str:
    """Reads a file if it exists, returns empty string otherwise."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def get_top_level_directory_structure(repo_path: str) -> str:
    """Returns a string representation of the top-level directory structure."""
    entries = os.listdir(repo_path)
    structure = []
    for entry in entries:
        full_path = os.path.join(repo_path, entry)
        if os.path.isdir(full_path):
            structure.append(f"{entry}/")
        else:
            structure.append(entry)
    return "\n".join(structure)

def gather_files_for_perspective(repo_path: str, perspective: Dict[str, Any], max_file_size: int = 10000) -> Dict[str, str]:
    """
    Gathers the content of entry point files and all files in key directories for a perspective.
    Truncates or summarizes files if they are too large.
    """
    files_content = {}
    
    # Gather entry point files
    for file_rel in perspective.get("entry_points_or_main_files", []):
        file_path = os.path.join(repo_path, file_rel)
        if os.path.exists(file_path):
            files_content[file_rel] = read_file_with_limit(file_path, max_file_size)
    
    # Gather files in key directories
    for dir_rel in perspective.get("key_directories", []):
        dir_path = os.path.join(repo_path, dir_rel)
        if os.path.isdir(dir_path):
            for root, _, files in os.walk(dir_path):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, repo_path)
                    if rel_path not in files_content:
                        files_content[rel_path] = read_file_with_limit(fpath, max_file_size)
    
    return files_content

def read_file_with_limit(path: str, max_size: int) -> str:
    """Reads a file with a size limit."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if len(content) > max_size:
                return content[:max_size] + "\n... (truncated)"
            return content
    except Exception:
        return ""

# Prompt building functions
def build_gemini_perspective_prompt(readme: str, config_files: List[tuple], dir_structure: str) -> str:
    """Builds the initial perspective detection prompt for Gemini."""
    config_str = "\n".join(
        [f"{fname}:\n{content[:1000]}{'... (truncated)' if len(content) > 1000 else ''}" 
         for fname, content in config_files]
    )
    
    return f"""
You are a senior software architect. Your task is to analyze a codebase and produce a structured JSON summary of its major functional perspectives (layers/modules).

**Instructions:**
1. Carefully read the provided README, configuration files, and the top-level directory structure.
2. Identify the main "perspectives" or "functional layers" in the codebase. Examples: "Frontend UI Layer", "Backend API Layer", "Business Logic/Service Layer", "Data Access/ORM Layer", "Authentication Module", etc.
3. For each perspective, provide:
    - A clear, human-readable name (e.g., "Frontend UI Layer").
    - A concise description of its purpose and technology (e.g., "React-based user interface").
    - The key directories where its code lives.
    - The main entry-point files for this perspective.

**Output Format:**
Return a single JSON object with the following structure:

{{
  "project_summary": "A 1-2 sentence summary of the overall project purpose and tech stack.",
  "detected_tech_stack": ["List", "of", "major", "technologies"],
  "identified_perspectives": [
    {{
      "perspective_name": "Frontend UI Layer",
      "details": "React-based user interface",
      "key_directories": ["client/src/components", "client/src/pages"],
      "entry_points_or_main_files": ["client/src/App.js", "client/src/index.js"]
    }},
    {{
      "perspective_name": "Backend API Layer",
      "details": "Django REST Framework API",
      "key_directories": ["server/api/views", "server/api/urls"],
      "entry_points_or_main_files": ["server/manage.py", "server/api/urls.py"]
    }}
  ]
}}

**Input Provided:**
- README.md content:
{readme[:2000]}{'... (truncated)' if len(readme) > 2000 else ''}

- Key config files:
{config_str}

- Top-level directory structure:
{dir_structure}

**Output:**
Return ONLY the JSON object, nothing else.
"""

def build_frontend_ui_layer_prompt(project_summary: str, perspective: Dict[str, Any], files_content: Dict[str, str]) -> str:
    """Builds the Frontend UI Layer analysis prompt for Gemini."""
    files_list = "\n".join([
        f"### {fname}\n```\n{content[:2000]}{'... (truncated)' if len(content) > 2000 else ''}\n```"
        for fname, content in files_content.items()
    ])
    
    return f"""
You are a Senior Frontend Architect. Analyze the provided Frontend UI Layer code files for a {perspective['details']} application. The overall project context is: {project_summary}

The relevant files are:
{files_list}

Provide a detailed breakdown structured as follows using Markdown:

### Frontend UI Layer Analysis: {perspective['perspective_name']}

#### 1. Core UI Components & Purpose:
For each major UI component file provided:
- **File:** `[filename]`
  - **Purpose/Responsibility:** (e.g., 'Renders the primary user login form')
  - **Key UI Elements Defined:** (e.g., 'Login button', 'Username input field')
  - **State Management (Local):** (How it manages its own state, if applicable)
  - **Props Received:** (Key props it expects and their purpose)

#### 2. API Endpoints Consumed & Data Flow:
- **Data Fetching Overview:** (How does this UI layer generally fetch data?)
- **Key API Interactions:**
  - **Feature/Component:** `[e.g., UserProfilePage]`
    - **Consumes API Endpoint:** `[e.g., GET /api/users/:id]`
    - **Purpose:** 'To fetch detailed user data for display.'
    - **Data Flow:** 'On page load, calls `fetchUserData(userId)`. Response data is stored in component state.'

#### 3. Navigation & Routing Structure:
- **Router Configuration File(s):** `[e.g., App.js, routes.js]`
- **Main Routes:**
  - **Path:** `[e.g., /profile/:userId]`
  - **Renders Component:** `[e.g., UserProfilePage]`
  - **Purpose:** 'Displays the profile for a specific user.'

#### 4. Global State Management (if detected):
- **Technology:** `[e.g., Redux, Zustand, Vuex, Context API]`
- **Key Store Modules/Slices:** `[e.g., authStore, userProfileStore]`
- **How UI Components Interact with Global State:** (e.g., 'UserProfilePage subscribes to `userProfileStore`')

#### 5. Noteworthy UI Logic or Patterns:
(e.g., 'Uses a custom hook `useAuth` for authentication checks', 'Implements lazy loading for images')

**You must return ONLY the Markdown output in the above structure.**
"""

def build_backend_api_layer_prompt(project_summary: str, perspective: Dict[str, Any], files_content: Dict[str, str]) -> str:
    """Builds the Backend API Layer analysis prompt for Gemini."""
    files_list = "\n".join([
        f"### {fname}\n```\n{content[:2000]}{'... (truncated)' if len(content) > 2000 else ''}\n```"
        for fname, content in files_content.items()
    ])
    
    return f"""
You are a Senior Backend Architect. Analyze the provided Backend API Layer code files for a {perspective['details']} application. The overall project context is: {project_summary}

The relevant files are:
{files_list}

Provide a detailed breakdown structured as follows using Markdown:

### Backend API Layer Analysis: {perspective['perspective_name']}

#### 1. API Endpoint Inventory & Specifications:
For each major API endpoint defined:
- **Endpoint Path & Method(s):** `[e.g., GET, POST /api/items/:id]`
  - **Controller/View Function:** `[e.g., ItemViewSet.retrieve, ItemViewSet.create]`
  - **Purpose:** (e.g., 'Retrieves a specific item by ID')
  - **Request Body (for POST/PUT/PATCH):** (Expected JSON structure)
  - **Response Body (Success):** (Typical JSON structure)
  - **Authentication/Authorization:** (e.g., 'Requires JWT authentication')
  - **Key Serializers Used:** `[e.g., ItemSerializer]`

#### 2. Core Logic Flow for Key Endpoints:
Select 2-3 critical endpoints:
- **Endpoint:** `[e.g., POST /api/orders]`
  - **Step 1 (Validation):** (e.g., 'Validates request body using OrderSerializer')
  - **Step 2 (Business Logic):** (e.g., 'Calls OrderService.createOrder')
  - **Step 3 (Data Persistence):** (e.g., 'Saves to database via OrderRepository')
  - **Step 4 (Response):** (e.g., 'Returns 201 Created with order data')
  - **Error Handling:** (How errors are caught and returned)

#### 3. Interaction with Other Layers/Services:
(e.g., 'ItemViewSet calls InventoryService', 'Auth logic delegated to AuthModule')

#### 4. Database Interaction:
- **Key Models/Entities:** `[e.g., Item, Order, User]`
- **ORM Usage:** (How the API layer uses the ORM)

#### 5. Noteworthy Design Patterns:
(e.g., 'Uses dependency injection', 'Implements caching for GET endpoints')

**You must return ONLY the Markdown output in the above structure.**
"""

def build_generic_perspective_prompt(project_summary: str, perspective: Dict[str, Any], files_content: Dict[str, str]) -> str:
    """Builds a generic analysis prompt for other perspectives."""
    files_list = "\n".join([
        f"### {fname}\n```\n{content[:2000]}{'... (truncated)' if len(content) > 2000 else ''}\n```"
        for fname, content in files_content.items()
    ])
    
    return f"""
You are a Senior Software Architect. Analyze the provided {perspective['perspective_name']} code files. The overall project context is: {project_summary}

The relevant files are:
{files_list}

Provide a detailed breakdown structured as follows using Markdown:

### {perspective['perspective_name']} Analysis

#### 1. Core Components & Purpose:
For each major component:
- **Component:** `[name]`
  - **Purpose:** (What does this component do?)
  - **Key Features:** (What are its main features?)
  - **Dependencies:** (What does it depend on?)

#### 2. Data Flow & Interactions:
- **Input Sources:** (Where does it get data from?)
- **Output Destinations:** (Where does it send data to?)
- **Key Interactions:** (How does it interact with other components?)

#### 3. Configuration & Setup:
- **Configuration Files:** (What config files are used?)
- **Environment Variables:** (What environment variables are needed?)
- **Dependencies:** (What external dependencies are required?)

#### 4. Notable Patterns & Practices:
(What design patterns or best practices are used?)

#### 5. Potential Improvements:
(What could be improved or optimized?)

**You must return ONLY the Markdown output in the above structure.**
"""

# Markdown parsing functions
def parse_frontend_ui_layer_markdown(markdown_text: str) -> Dict[str, Any]:
    """Parses the Frontend UI Layer markdown into a structured JSON."""
    markdown = mistune.create_markdown(renderer=mistune.AstRenderer())
    ast = markdown(markdown_text)
    
    # TODO: Implement proper AST traversal and JSON conversion
    # For now, return the raw markdown
    return {"raw_markdown": markdown_text}

def parse_backend_api_layer_markdown(markdown_text: str) -> Dict[str, Any]:
    """Parses the Backend API Layer markdown into a structured JSON."""
    markdown = mistune.create_markdown(renderer=mistune.AstRenderer())
    ast = markdown(markdown_text)
    
    # TODO: Implement proper AST traversal and JSON conversion
    # For now, return the raw markdown
    return {"raw_markdown": markdown_text}

def parse_generic_markdown(markdown_text: str) -> Dict[str, Any]:
    """Parses generic markdown into a structured JSON."""
    markdown = mistune.create_markdown(renderer=mistune.AstRenderer())
    ast = markdown(markdown_text)
    
    # TODO: Implement proper AST traversal and JSON conversion
    # For now, return the raw markdown
    return {"raw_markdown": markdown_text} 