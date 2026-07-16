# PPT-Excel ETL Automation API & Antigravity Prompt

This document provides a complete REST API specification for the PPT-Excel ETL automation tool, along with a comprehensive prompt you can use to have Antigravity build the entire application.

## 1. API Specification

The API is designed to handle the step-by-step nature of the workflow, from file uploads to extraction, mapping, and the final generation of the updated PowerPoint file.

### Base URL: `/api/v1/etl`

### Endpoints

#### **Project Initialization**
- **`POST /projects`**
  - **Description**: Initializes a new ETL project session.
  - **Response**: `{ "project_id": "uuid", "status": "created" }`

#### **Step 1: Upload & Extract PPT**
- **`POST /projects/{project_id}/upload-ppt`**
  - **Description**: Uploads the PowerPoint file. The backend parses slides, extracts text boxes, shapes, signs, and special characters (↑, ↓, →, ←, %, #). **Note: Instruction formats are highly dynamic and will not be the same across different PPT slides. The parsing logic must adapt to unstructured, non-uniform variations.**
  - **Payload**: `multipart/form-data` (file: .pptx)
  - **Response**: Returns an array of extracted instructions.
  ```json
  {
    "instructions": [
      { "id": 1, "slide_number": 2, "raw_text": "{Data} - Table_1, S1, Column - Total", "type": "instruction" },
      { "id": 2, "slide_number": 3, "raw_text": "↑", "type": "symbol" }
    ]
  }
  ```

#### **Step 2: Upload Excel & Normalize**
- **`POST /projects/{project_id}/upload-excel`**
  - **Description**: Uploads the Excel file. Scans tables, normalizes names (e.g., Table_1 ↔ Table 1), and memorizes question codes.
  - **Payload**: `multipart/form-data` (file: .xlsx)
  - **Response**: `{ "status": "success", "tables_detected": 15, "normalized_names": [...] }`

#### **Step 3: Compare & Extract Data**
- **`POST /projects/{project_id}/extract-data`**
  - **Description**: Matches PPT instructions to Excel tables and pulls corresponding data.
  - **Response**: 
  ```json
  {
    "status": "extracted",
    "matches_found": 12,
    "download_url": "/api/v1/etl/projects/{project_id}/download-extracted-excel"
  }
  ```
- **`GET /projects/{project_id}/download-extracted-excel`**
  - **Description**: Downloads the separate Excel file containing only the extracted matched data.

#### **Step 4 & 5: Map & Paste (Graph/Symbol Rendering)**
- **`POST /projects/{project_id}/map-and-paste`**
  - **Description**: Applies the Graph-Type Decision Map. Generates charts (Pie, Bar, Stacked, Heatmap) or handles special characters, and pastes them back into the exact PPT slide locations.
  - **Response**: 
  ```json
  {
    "status": "completed",
    "download_url": "/api/v1/etl/projects/{project_id}/download-final-ppt"
  }
  ```

#### **Step 6: Download Final PPT**
- **`GET /projects/{project_id}/download-final-ppt`**
  - **Description**: Downloads the final updated PowerPoint file with all charts and symbols inserted.

---

## 2. Antigravity Build Prompt

*Copy and paste the following prompt into your Antigravity session to build this application. Since I am Antigravity, you can also just tell me "Let's build this right now" in our current conversation, and I will begin!*

***

### 📋 Antigravity Build Prompt

```markdown
**Role & Goal:**
You are Antigravity, an expert AI coding assistant. I want you to build a full-stack web application that automates an ETL and Decision Mapping workflow between PowerPoint (PPT) and Excel.

**Tech Stack Requirements:**
- **Backend**: Python (FastAPI or Flask) - *Required because we need libraries like `python-pptx` and `pandas`/`openpyxl` for advanced PPT/Excel manipulation.*
- **Frontend**: React or Next.js with vanilla CSS or TailwindCSS. Make the UI highly aesthetic, premium, modern, and dynamic.
- **Architecture**: Create an API-first backend and a client-side frontend that consumes it.

**Core Workflow & Logic:**
The application must perform the following cycle based on ETL + Decision Mapping:

1. **Step 1: Upload PPT (Extract)**
   - Expose an endpoint to upload a PPT.
   - Parse the PPT. IMPORTANT: Do not assume instructions are always in standard text boxes. They can be in varying shapes, and sometimes they aren't explicit text instructions but rather signs, special characters, or arrows (↑, ↓, →, ←, %, #).
   - **CRITICAL**: The format of instructions will NEVER be perfectly uniform or identical across PPT slides. Instructions are highly dynamic, and you must ensure the parsing logic expects varying, unstructured formats on every single slide rather than hardcoding a single matching pattern. You must parse everything and gracefully handle variations.
   - The frontend should display these extracted instructions in a sortable table.

2. **Step 2: Upload Excel (Transform)**
   - Expose an endpoint to upload an Excel file.
   - Scan all tables and memorize question codes.
   - Apply Name Normalization (e.g., convert "Table_1" ↔ "Table 1") for universal matching so mismatches don't break the automation.

3. **Step 3: Compare & Extract (Load)**
   - Match the PPT instructions/symbols to the Excel tables/data.
   - Pull the corresponding data values.
   - Generate and save the extracted data into a separate, downloadable Excel file using the matched table/question names.

4. **Step 4: Map & Paste (Decision Map)**
   - Implement a Graph-Type Decision Map on the backend:
     - Gender → Pie chart
     - Age / Education → Bar chart
     - Marital Status → Pie chart
     - Concern Levels → Stacked bar chart
     - Cross-tab → Grouped bar chart / Heatmap
     - Ranked Statements → Horizontal bar chart
     - Special characters/signs (↑, ↓, etc.) → Fallback handling (text markers, symbolic representations, or conditional formatting instead of a graph).
   - Paste the generated graph, data, or symbol back into the exact original PPT slide box/location where the instruction was found.

5. **Step 5: Client Controls (UI/UX)**
   - **Left side panel**: Workflow navigation with steps: Upload PPT → Upload Excel → Proceed.
   - **Top header bar**: Include a "Sorting" button to organize the extracted instructions table, and a "Map" button to trigger the map-and-paste logic.

**Critical Requirements for Robustness:**
- PPTs and Excel files will vary in structure every time. The parsing logic must be highly flexible.
- Implement robust fallback mechanisms for missing boxes or unmatched data.
- The UI must look incredibly premium. Use a cohesive color palette, micro-animations, and a modern layout.

Please act in Planning Mode first:
1. Propose an implementation plan detailing the folder structure, Python libraries you will use, and the frontend component hierarchy.
2. Wait for my approval before executing the code generation.
```
