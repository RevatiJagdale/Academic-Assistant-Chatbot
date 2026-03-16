# backend/main.py
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Import Services ---
from rag_service import query_rag_module, LLM  
import ingestion_service as ingest
from timetable_tool import TimetableTool   
from inventory_tool import InventoryTool  

app = FastAPI(title="EEEVA: Tool-Augmented Academic Chatbot")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Your Next.js app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class Question(BaseModel):
    question: str

# --- LOAD TOOLS ON STARTUP ---
# Load the timetable tool once when the app starts
try:
    timetable_tool = TimetableTool()
except FileNotFoundError as e:
    print(f"[ERROR] {e}")
    print("[ERROR] Timetable tool disabled. Please add data/timetable.csv and restart.")
    timetable_tool = None
except Exception as e:
    print(f"[ERROR] Failed to load TimetableTool: {e}")
    timetable_tool = None

try:
    inventory_tool = InventoryTool()  # <-- ADD THIS BLOCK
except FileNotFoundError as e:
    print(f"[ERROR] {e}")
    inventory_tool = None
except Exception as e:
    print(f"[ERROR] Failed to load InventoryTool: {e}")
    inventory_tool = None


# backend/main.py

# --- NEW, STRICT RAG PROMPT ---
STRICT_RAG_PROMPT = """
You are a factual data retrieval bot. Your task is to answer the user's question using ONLY the provided context.
**Do not, under any circumstances, use your own knowledge or hallucinate.**

Context:
{context}

User Question: {question}

Instructions:
1.  If the answer is in the context, extract it directly.
2.  If the answer is not in the context, you MUST say "I could not find that information in the provided documents."
3.  **Format all lists as a simple HTML `<ul>` with `<li>` tags.** For example: <ul><li>Item 1</li><li>Item 2</li></ul>
4.  Use `<br>` tags for newlines. Do not add any extra conversation.

Answer:
"""

# --- NEW, STRICT TIMETABLE PROMPT ---
TIMETABLE_PROMPT_TEMPLATE = """
You are a factual data retrieval bot. Answer the user's question using ONLY the provided data.
**Do not, under any circumstances, use your own knowledge or hallucinate.**

User Question: {question}

Data from Timetable Tool:
{context}

Instructions:
1.  **If the data provides a list (e.g., of faculty or rooms):** State that list clearly. **Use an HTML `<ul>` with `<li>` tags.**
2.  **If the data says "No faculty are free" or "No classrooms are free":** Report this fact directly.
3.  **If the data says "Could not find a valid time slot":** State that the time slot could not be found.
4.  **Use `<br>` tags for newlines.** Do not use Markdown.

Answer:
"""

# --- NEW, STRICT INVENTORY PROMPT ---
INVENTORY_PROMPT_TEMPLATE = """
You are a factual data retrieval bot. Answer the user's question using ONLY the provided data.
Do not make up information.

User Question: {question}

Data from Inventory Tool:
{context}

Instructions:
1.  Report the data directly. (e.g., "Total quantity for 'Oscilloscope': 25 units.")
2.  **Format any lists as a simple HTML `<ul>` with `<li>` tags.**
3.  If the tool says "No items found", state that.
4.  **Use `<br>` tags for newlines.**

Answer:
"""

# --- Module Definitions ---
# Store paths and prompts in one place
MODULE_CONFIGS = {
    "syllabus": {
        "db_path": os.path.join("chroma", "syllabus"),
        "prompt": """
Answer the question based only on the following syllabus context:
{context}
---
Question: {question}
""",
        "not_found": "No relevant syllabus content found for that query."
    },
    # REMOVED timetable RAG config, as it's now a tool.
    "labmanual": {
        "db_path": os.path.join("chroma", "labmanual"),
        "prompt": """
Answer the question based only on the following lab manual context.
Provide details like aim, apparatus, or procedure if asked.
{context}
---
Question: {question}
""",
        "not_found": "That experiment or procedure was not found in the lab manuals."
    },
    "inventory": {
        "db_path": os.path.join("chroma", "inventory"),
        "prompt": """
Answer the question based only on the following lab inventory data.
State the equipment, quantity, location, or condition as requested.
{context}
---
Question: {question}
""",
        "not_found": "That equipment was not found in the inventory."
    }
}

# --- 1. Direct Query Endpoints (For UI Buttons) ---

@app.post("/api/query/syllabus")
def query_syllabus_endpoint(payload: Question):
    config = MODULE_CONFIGS["syllabus"]
    return query_rag_module(
        payload.question, config["db_path"], config["prompt"], config["not_found"]
    )

@app.post("/api/query/timetable")
def query_timetable_endpoint(payload: Question):
    """
    Uses the Pandas tool to get data, then an LLM to make it conversational.
    """
    if not timetable_tool:
        return {"answer": "The timetable tool is not loaded. Please check backend logs.", "sources": []}
        
    # 1. Get the ACCURATE data from your Pandas logic
    raw_data_answer = timetable_tool.query_timetable(payload.question)
    
    # 2. Pass that data as CONTEXT to the LLM to be "rephrased"
    prompt = TIMETABLE_PROMPT_TEMPLATE.format(
        question=payload.question,
        context=raw_data_answer
    )
    
    try:
        # Use the same LLM from rag_service
        response = LLM.invoke(prompt).content
    except Exception as e:
        print(f"[ERROR] LLM rephrasing failed: {e}")
        # Fallback to the raw data if LLM fails
        response = raw_data_answer

    # 3. Format the final LLM-generated answer
    return {
        "answer": response,
        "sources": [{
            "source": "timetable.csv", 
            "score": 1.0, 
            "content_preview": raw_data_answer[:100] + "..."
        }]
    }

@app.post("/api/query/labmanual")
def query_labmanual_endpoint(payload: Question):
    config = MODULE_CONFIGS["labmanual"]
    return query_rag_module(
        payload.question, config["db_path"], config["prompt"], config["not_found"]
    )

@app.post("/api/query/inventory")
def query_inventory_endpoint(payload: Question):
    config = MODULE_CONFIGS["inventory"]
    return query_rag_module(
        payload.question, config["db_path"], config["prompt"], config["not_found"]
    )


# --- 2. Agentic Query Endpoint (For Main Chat Box) ---

# --- 2. Agentic Query Endpoint (For Main Chat Box) ---

@app.post("/api/query/inventory")  # <-- ADD THIS NEW ENDPOINT
def query_inventory_endpoint(payload: Question):
    """
    Uses the Pandas tool to get data, then an LLM to make it conversational.
    """
    if not inventory_tool:
        return {"answer": "The inventory tool is not loaded. Please check backend logs.", "sources": []}
        
    raw_data_answer = inventory_tool.query_inventory(payload.question)
    
    prompt = INVENTORY_PROMPT_TEMPLATE.format(
        question=payload.question,
        context=raw_data_answer
    )
    
    try:
        response = LLM.invoke(prompt).content
    except Exception as e:
        print(f"[ERROR] LLM rephrasing failed: {e}")
        response = raw_data_answer

    return {
        "answer": response,
        "sources": [{"source": "inventory.xlsx", "score": 1.0}]
    }

def detect_intent(question: str) -> str:
    """
    Simple rule-based intent detection.
    (Demo Cheat Sheet Version)
    """
    q_lower = question.lower()
    
    # --- Inventory Keywords ---
    if any(k in q_lower for k in [
        "how many", "inventory", "equipment", "component", 
        "available", "where is", "where are", "condition of",
        "multimeter", "pliers", "oscilloscope", "fpga", "soldering",
        "deadstock", "in lab 1", "in lab 2", "in lab 3",
        "logic analyzer", "do we have", "breadboard"
    ]):
        return "inventory"

    # --- Timetable Keywords ---
    if any(k in q_lower for k in [
        "free", "schedule", "who teaches", "class at", "faculty", 
        "timetable", "room", "venue", "classroom", "tomorrow", 
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
        "available", "classes", "empty rooms"
    ]):
        return "timetable"
        
    # --- Lab Manual Keywords ---
    if any(k in q_lower for k in [
        "experiment", "procedure", "apparatus", "aim", "viva", "lab manual"
    ]):
        return "labmanual"
        
    # --- Syllabus Keywords (Default) ---
    # We can add a few high-priority syllabus words here
    if any(k in q_lower for k in [
        "mission", "vision", "outcomes", "objectives", "dean",
        "topics", "module", "batch", "textbook", "book", "syllabus"
    ]):
        return "syllabus"
        
    # Default to syllabus for any general question
    return "syllabus"

@app.post("/api/query/eeeva")
def query_agentic_endpoint(payload: Question):
    """
    The main "agentic" endpoint.
    It detects intent and routes to the correct module.
    """
    intent = detect_intent(payload.question)
    print(f"[EEEVA Agent] Detected Intent: {intent}")
    
    if intent == "syllabus":
        return query_syllabus_endpoint(payload)
    elif intent == "timetable":
        return query_timetable_endpoint(payload)
    elif intent == "labmanual":
        return query_labmanual_endpoint(payload)
    elif intent == "inventory":  # <-- ADDED THIS
        return query_inventory_endpoint(payload)
    else:
        # Fallback
        return query_syllabus_endpoint(payload)

# --- 3. File Upload Endpoints ---

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_upload_file_temp(upload_file: UploadFile) -> str:
    """Saves a file to a temporary location and returns the path."""
    try:
        file_path = os.path.join(UPLOAD_DIR, upload_file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        return file_path
    finally:
        upload_file.file.close()

@app.post("/api/upload/file")
async def upload_file(file: UploadFile = File(...)):
    """
    A single, smart endpoint to handle all file uploads.
    It routes files to the correct location or tool.
    """
    filename = file.filename.lower()
    
    try:
        # --- Route 1: Timetable Tool ---
        if "timetable.csv" in filename:
            save_path = "data/timetable.csv"
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file.file.close()
            
            # Reload the tool in memory
            global timetable_tool
            timetable_tool = TimetableTool() 
            print("[INFO] Timetable tool reloaded after file upload.")
            return {"status": "success", "message": "Timetable has been updated."}

        # --- Route 2: Inventory Tool ---
        elif "inventory.xlsx" in filename:
            save_path = "data/inventory.xlsx"
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file.file.close()

            # Reload the tool in memory
            global inventory_tool
            inventory_tool = InventoryTool()
            print("[INFO] Inventory tool reloaded after file upload.")
            return {"status": "success", "message": "Inventory has been updated."}
            
        # --- Route 3: RAG Documents (PDF/DOCX) ---
        elif filename.endswith((".pdf", ".docx")):
            # Save to a temp location for ingestion
            temp_path = save_upload_file_temp(file)
            
            # Ingest this single new file
            ingest.ingest_document(temp_path)
            
            os.remove(temp_path) # Clean up temp file
            return {"status": "success", "message": f"Document {file.filename} has been ingested."}
        
        # --- Route 4: Fallback ---
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Please upload 'timetable.csv', 'inventory.xlsx', or a .pdf/.docx file."
            )
            
    except Exception as e:
        print(f"[UPLOAD ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {e}")