#!/usr/bin/env python3
import sys
import logging
from datetime import datetime
from pathlib import Path
import os
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import core logic from service modules
from GPC import export_code_lists, load_to_postgres
from Bio_Certificaat import main as certificate
from APIData import strategy_direct_json

# ─── FASTAPI SETUP ─────────────────────────────────────────────────────────
app = FastAPI(
    title="GPC Automations API",
    description="API voor Excel-imports, Access-exports en Floricode-queries",
    version="1.0.0"
)
router = APIRouter()

# Allow CORS broadly for now (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://frontend-1-jb75.onrender.com","*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

# ─── ROOT & HEALTH ─────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    """
    Simple root endpoint so `GET /` and `HEAD /` return 200.
    """
    return {"status": "ok"}

@router.get("/health", tags=["Health"])
def health_check():
    logger.info("Health check invoked")
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# ─── AUTOMATIONS ────────────────────────────────────────────────────────────
@router.post("/import/import-excel", tags=["Automations"])
def api_import_excel():
    debug_steps = []
    try:
        debug_steps.append("Starting Floricode data fetch")
        strategy_direct_json()
        debug_steps.append("Floricode data fetch completed")

        debug_steps.append("Starting Excel import")
        out_path = load_to_postgres()
        debug_steps.append(f"Excel import completed: {out_path}")

    except Exception as e:
        error_msg = str(e)
        debug_steps.append(f"Error occurred: {error_msg}")
        logger.error(f"Excel-import pipeline failed: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail={"error": error_msg, "debug": debug_steps}
        )

    return {"message": "Excel-import voltooid", "file": str(out_path), "debug": debug_steps}

@router.post("/access/run-access", tags=["Automations"])
def api_run_access():
    debug_steps = []
    try:
        debug_steps.append("Starting Access queries & export")
        zip_path = export_code_lists()
        debug_steps.append(f"Access export completed: {zip_path}")

    except Exception as e:
        error_msg = str(e)
        debug_steps.append(f"Error occurred: {error_msg}")
        logger.error(f"Access-export pipeline failed: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail={"error": error_msg, "debug": debug_steps}
        )

    return {"message": "Access-export voltooid", "zip": str(zip_path), "debug": debug_steps}

@router.post("/biocertificate", tags=["Automations"])
def api_run_biocertificate():
    debug_steps = []
    try:
        debug_steps.append("Starting Data-Extraction ")
        certificate()
        debug_steps.append("Data-Extraction completed")

    except Exception as e:
        error_msg = str(e)
        debug_steps.append(f"Error occurred: {error_msg}")
        logger.error(f"Data-Extraction pipeline failed: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail={"error": error_msg, "debug": debug_steps}
        )

    return {"message": "Data-Extraction voltooid", "debug": debug_steps}


# ─── Uvicorn LAUNCH (DEV ONLY) ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
