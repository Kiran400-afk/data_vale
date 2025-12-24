from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import shutil
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .validator_engine import ValidatorEngine
from .services.column_mapper import ColumnMapper
from .services.root_cause_engine import RootCauseEngine
from .services.fix_suggestion_engine import FixSuggestionEngine
from .services.gemini_assistant import GeminiAssistant
from .services.report_generator import ReportGenerator
from .services.auth import verify_credentials, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from .services.session_db import store_session, delete_session, get_session
from typing import Optional
import json
from io import BytesIO
from pathlib import Path
import numpy as np
import pandas as pd

def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    return obj

# Resolve frontend build path
FRONTEND_BUILD = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

app = FastAPI(title="Advanced AI Data Validator")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory store for demo (should use a database/cache for production)
validation_sessions = {}

# ==================== AUTH ENDPOINTS ====================
from datetime import datetime, timedelta
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/login")
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    if not verify_credentials(request.username, request.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    # Create access token
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": request.username},
        expires_delta=expires_delta
    )
    
    # Store session in database
    expires_at = datetime.utcnow() + expires_delta
    store_session(access_token, request.username, expires_at)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": request.username,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    }

@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user and invalidate token."""
    delete_session(current_user["token"])
    return {"message": "Successfully logged out"}

@app.get("/auth/verify")
async def verify_auth(current_user: dict = Depends(get_current_user)):
    """Verify if the current token is valid."""
    return {
        "authenticated": True,
        "username": current_user["username"]
    }

# ==================== MAIN ENDPOINTS ====================

@app.get("/")
def read_root():
    # Serve frontend if built, otherwise return API message
    index_file = FRONTEND_BUILD / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "AI Data Validation API is active"}

@app.post("/upload")
async def upload_files(
    gold_file: UploadFile = File(...),
    growth_file: UploadFile = File(...),
    threshold: float = Form(3.0)
):
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    gold_ext = gold_file.filename.lower().split('.')[-1] if '.' in gold_file.filename else 'csv'
    growth_ext = growth_file.filename.lower().split('.')[-1] if '.' in growth_file.filename else 'csv'
    
    gold_path = os.path.join(session_dir, f"gold.{gold_ext}")
    growth_path = os.path.join(session_dir, f"growth.{growth_ext}")
    
    with open(gold_path, "wb") as buffer:
        shutil.copyfileobj(gold_file.file, buffer)
    with open(growth_path, "wb") as buffer:
        shutil.copyfileobj(growth_file.file, buffer)
        
    # Initialize Validator Engine
    try:
        engine = ValidatorEngine(threshold_percent=threshold)
        engine.load_data(growth_path, gold_path)  # Note: growth is CSV, gold is Fabric
    except Exception as e:
        # Return specific error to frontend
        raise HTTPException(status_code=400, detail=str(e))
    
    # PHASE 3: Column Mapping
    mapper = ColumnMapper(engine.csv_df, engine.fabric_df)
    column_mappings = mapper.auto_map()
    mapping_warnings = mapper.validate_mapping(column_mappings)
    
    import time
    start_time = time.time()
    
    # Run validation
    results = engine.validate_all()
    summary = engine.get_summary_stats()
    
    # PHASE 6: Root Cause Analysis
    root_cause_engine = RootCauseEngine(engine.csv_df, engine.fabric_df)
    root_causes = root_cause_engine.analyze(results)
    
    # PHASE 7: Fix Suggestions
    fixes = FixSuggestionEngine.generate_fixes(root_causes)
    
    duration = time.time() - start_time
    print(f"⏱️ Validation completed in {duration:.2f}s")
    
    # Store in memory for later access (AI summary removed from here)
    validation_sessions[session_id] = {
        "engine": engine,
        "summary": summary,
        "results": results,
        "column_mappings": column_mappings,
        "mapping_warnings": mapping_warnings,
        "root_causes": root_causes,
        "fixes": fixes,
        "ai_summary": None # Lazy load this
    }
    
    return {
        "session_id": session_id,
        "summary": summary,
        "column_mappings": column_mappings,
        "mapping_warnings": mapping_warnings
    }

@app.post("/preview-columns")
async def preview_columns(
    gold_file: UploadFile = File(...),
    growth_file: UploadFile = File(...)
):
    """Extract column names and sample data from both files for the mapping UI."""
    import pandas as pd
    
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # Save files temporarily
    gold_path = os.path.join(session_dir, gold_file.filename)
    growth_path = os.path.join(session_dir, growth_file.filename)
    
    with open(gold_path, "wb") as f:
        f.write(await gold_file.read())
    with open(growth_path, "wb") as f:
        f.write(await growth_file.read())
    
    # Robust file reader that handles various formats and encodings
    def read_file(path):
        import pandas as pd
        file_ext = path.lower().split('.')[-1]
        
        # Excel files
        if file_ext in ['xlsx', 'xls']:
            try:
                # Try reading with different header rows
                for skiprows in [0, 1, 2, 3]:
                    try:
                        df = pd.read_excel(path, skiprows=skiprows, nrows=15)
                        # Check if we have valid column names
                        if not any(str(c).startswith('Unnamed') for c in df.columns[:3]):
                            return df.head(10)
                    except:
                        continue
                return pd.read_excel(path, nrows=10)
            except Exception as e:
                print(f"Excel read error: {e}")
                return pd.DataFrame()
        
        # CSV files - try multiple encodings and skip rows
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16', 'utf-8-sig']
        
        for encoding in encodings:
            for skiprows in [0, 1, 2, 3]:
                try:
                    df = pd.read_csv(path, encoding=encoding, skiprows=skiprows, nrows=15, on_bad_lines='skip')
                    # Check if columns look valid (not Unnamed or empty)
                    if len(df.columns) > 0:
                        unnamed_count = sum(1 for c in df.columns if str(c).startswith('Unnamed') or str(c).strip() == '')
                        if unnamed_count < len(df.columns) / 2:  # At least half should be valid
                            # Filter out Unnamed columns
                            valid_cols = [c for c in df.columns if not str(c).startswith('Unnamed') and str(c).strip() != '']
                            if valid_cols:
                                return df[valid_cols].head(10)
                except Exception:
                    continue
        
        # Last resort - just read it
        try:
            return pd.read_csv(path, nrows=10, on_bad_lines='skip')
        except:
            return pd.DataFrame()
    
    gold_df = read_file(gold_path)
    growth_df = read_file(growth_path)
    
    # Extract column info with sample data - filter out Unnamed columns
    def get_column_info(df):
        cols = []
        for col in df.columns:
            # Skip Unnamed columns and empty column names
            col_str = str(col).strip()
            if col_str.startswith('Unnamed') or col_str == '' or col_str.lower() == 'nan':
                continue
            sample = df[col].dropna().head(3).astype(str).tolist()
            cols.append({
                "name": col,
                "dtype": str(df[col].dtype),
                "sample": sample
            })
        return cols
    
    gold_columns = get_column_info(gold_df)
    growth_columns = get_column_info(growth_df)
    
    # DYNAMIC COLUMN MATCHING: Auto-detect all potential matches
    # First, try to match columns with similar names between both files
    suggested_mappings = []
    matched_gold = set()
    matched_growth = set()
    
    # Helper to normalize column names for comparison
    def normalize_name(name):
        return str(name).lower().replace('_', ' ').replace('-', ' ').strip()
    
    # Helper to check similarity
    def is_similar(name1, name2):
        n1, n2 = normalize_name(name1), normalize_name(name2)
        # Exact match
        if n1 == n2:
            return True
        # One contains the other
        if n1 in n2 or n2 in n1:
            return True
        # Common keywords match
        words1 = set(n1.split())
        words2 = set(n2.split())
        common = words1 & words2
        if common and len(common) >= 1:
            return True
        return False
    
    # First pass: Find matching columns between both files
    for gc in gold_columns:
        for grc in growth_columns:
            if is_similar(gc['name'], grc['name']):
                if gc['name'] not in matched_gold and grc['name'] not in matched_growth:
                    # Use the growth column name as the target (more readable usually)
                    target_name = normalize_name(grc['name']).replace(' ', '_')
                    suggested_mappings.append({
                        "target": target_name,
                        "gold_column": gc['name'],
                        "growth_column": grc['name'],
                        "auto_matched": True
                    })
                    matched_gold.add(gc['name'])
                    matched_growth.add(grc['name'])
                    break
    
    # Second pass: Add unmatched columns that might still be useful (numeric only for validation)
    for gc in gold_columns:
        if gc['name'] not in matched_gold and gc['dtype'] in ['int64', 'float64', 'int32', 'float32']:
            target_name = normalize_name(gc['name']).replace(' ', '_')
            suggested_mappings.append({
                "target": target_name,
                "gold_column": gc['name'],
                "growth_column": None,
                "auto_matched": False
            })
    
    for grc in growth_columns:
        if grc['name'] not in matched_growth and grc['dtype'] in ['int64', 'float64', 'int32', 'float32']:
            target_name = normalize_name(grc['name']).replace(' ', '_')
            # Check if target already exists
            existing = next((m for m in suggested_mappings if m['target'] == target_name), None)
            if not existing:
                suggested_mappings.append({
                    "target": target_name,
                    "gold_column": None,
                    "growth_column": grc['name'],
                    "auto_matched": False
                })
    
    return {
        "session_id": session_id,
        "gold_path": gold_path,
        "growth_path": growth_path,
        "gold_columns": gold_columns,
        "growth_columns": growth_columns,
        "suggested_mappings": suggested_mappings
    }

@app.post("/validate-with-mappings")
async def validate_with_mappings(
    session_id: str = Form(...),
    gold_path: str = Form(...),
    growth_path: str = Form(...),
    growth_mappings: str = Form(...),
    gold_mappings: str = Form(...),
    threshold: float = Form(3.0)
):
    """Run validation with custom column mappings for both files."""
    import json
    
    # Parse column mappings
    growth_col_mappings = json.loads(growth_mappings)
    gold_col_mappings = json.loads(gold_mappings)
    
    # Debug: log received mappings
    print("\n" + "="*60)
    print("🔍 RECEIVED COLUMN MAPPINGS FROM FRONTEND:")
    print(f"   Growth mappings: {growth_col_mappings}")
    print(f"   Gold mappings: {gold_col_mappings}")
    print("="*60 + "\n")
    
    # Initialize validation engine with custom mappings for both files
    engine = ValidatorEngine(
        threshold_percent=threshold, 
        custom_column_mappings=growth_col_mappings,
        gold_column_mappings=gold_col_mappings
    )
    engine.load_data(growth_path, gold_path)  # growth is CSV, gold is Fabric
    
    # Run validation
    results = engine.validate_all()
    summary = engine.get_summary_stats()
    
    # Root cause analysis
    root_cause_engine = RootCauseEngine(engine.csv_df, engine.fabric_df)
    root_causes = root_cause_engine.analyze(results)
    
    # Fix suggestions
    fixes = FixSuggestionEngine.generate_fixes(root_causes)
    
    # Store session
    validation_sessions[session_id] = {
        "engine": engine,
        "summary": summary,
        "results": results,
        "column_mappings": {"growth": growth_col_mappings, "gold": gold_col_mappings},
        "mapping_warnings": [],
        "root_causes": root_causes,
        "fixes": fixes,
        "ai_summary": None
    }
    
    return {
        "session_id": session_id,
        "summary": summary,
        "column_mappings": {"growth": growth_col_mappings, "gold": gold_col_mappings}
    }

@app.get("/results/{session_id}")
async def get_results(session_id: str):
    if session_id not in validation_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = validation_sessions[session_id]
    return convert_numpy_types({
        "results": session["results"],
        "root_causes": session.get("root_causes", []),
        "fixes": session.get("fixes", [])
    })

@app.post("/results/{session_id}/filter")
async def filter_results(
    session_id: str,
    campaigns: Optional[str] = None, # JSON or comma separated
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None # 'PASS' or 'FAIL'
):
    if session_id not in validation_sessions:
        return {"error": "Session not found"}
    
    # Logic to filter the DataFrames and rerun validation or filter existing dicts
    # (For MVP, we'll return the full results and handle filtering in Frontend)
    # But we can add Backend filtering for "Advanced" scale.
    
    return {"message": "Filter logic placeholder"}

@app.get("/results/{session_id}/ai-insight")
async def get_ai_insight(session_id: str):
    if session_id not in validation_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = validation_sessions[session_id]
    
    # Lazy generation of AI summary
    if session.get("ai_summary") is None:
        try:
            print(f"🤖 Generating AI summary for session {session_id}...")
            ai_assistant = GeminiAssistant()
            ai_summary = ai_assistant.generate_summary(
                {"summary": session["summary"], "results": session["results"]},
                session.get("root_causes", []),
                session.get("fixes", [])
            )
            session["ai_summary"] = ai_summary
        except Exception as e:
            session["ai_summary"] = f"AI summary unavailable: {str(e)}"
    
    return {
        "summary": session.get("ai_summary", "AI summary not available"),
        "root_causes": session.get("root_causes", []),
        "fixes": session.get("fixes", [])
    }

@app.post("/results/{session_id}/chat")
async def chat_with_ai(session_id: str, question: dict):
    """Interactive chat with Gemini about validation results."""
    if session_id not in validation_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = validation_sessions[session_id]
    user_question = question.get("question", "")
    
    if not user_question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    try:
        # Convert numpy types for JSON serialization
        context = convert_numpy_types({
            "summary": session["summary"], 
            "results": session["results"]
        })
        
        ai_assistant = GeminiAssistant()
        answer = ai_assistant.answer_question(user_question, context)
        return {"answer": answer}
    except Exception as e:
        print(f"❌ Chat AI error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")

@app.get("/results/{session_id}/export/html")
async def export_html_report(session_id: str):
    """Generate and download a comprehensive HTML report."""
    if session_id not in validation_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = validation_sessions[session_id]
    
    # Generate HTML report
    html_content = ReportGenerator.generate_html_report(
        validation_results=session["results"],
        summary=session["summary"],
        threshold=session["engine"].threshold_percent
    )
    
    # Return as downloadable file
    return HTMLResponse(
        content=html_content,
        headers={
            "Content-Disposition": f"attachment; filename=nyx_validation_report_{session_id[:8]}.html"
        }
    )

# Serve static files from frontend build
if FRONTEND_BUILD.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_BUILD / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for any non-API route."""
        index_file = FRONTEND_BUILD / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"error": "Frontend not built. Run 'npm run build' in frontend directory."}
