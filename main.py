#!/usr/bin/env python3
import sys
import logging
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import core logic from service modules
from GPC import excel_import_python, run_access_queries
from Bio_Certificaat import main as certificate

from APIData import strategy_direct_json

# ─── FASTAPI SETUP ─────────────────────────────────────────────────────────
app = FastAPI(
    title="GPC Automations API",
    description="API voor Excel-imports, Access-exports en Floricode-queries",
    version="1.0.0"
)
router = APIRouter()

# Allow CORS for React dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

# ─── ROUTES ────────────────────────────────────────────────────────────────
@router.get("/health", tags=["Health"])
def health_check():
    logger.info("Health check invoked")
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@router.post("/import/import-excel", tags=["Automations"])
def api_import_excel():
    debug_steps = []
    try:
        debug_steps.append("Starting Floricode data fetch")
        strategy_direct_json()
        debug_steps.append("Floricode data fetch completed")

        debug_steps.append("Starting Excel import")
        out_path = excel_import_python()
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
        zip_path = run_access_queries()
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

@router.post("/biocertificate/scraper", tags=["Automations"])
def api_run_biocertificate():
    debug_steps = []
    try:
        debug_steps.append("Starting Data-Extraction ")
        certificate()
        
    except Exception as e:
        error_msg = str(e)
        debug_steps.append(f"Error occurred: {error_msg}")
        logger.error(f"Data-Extraction  pipeline failed: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail={"error": error_msg, "debug": debug_steps}
        )

    return {"message": "Data-Extraction voltooid", "debug": debug_steps}

# Include the same router under BOTH /v1 and root (/) prefixes:
app.include_router(router, prefix="/v1")
app.include_router(router, prefix="")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",     # or just app if you prefer
        host="0.0.0.0",
        port=8000,
        reload=True
    )
