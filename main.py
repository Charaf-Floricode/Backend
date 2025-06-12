#!/usr/bin/env python3
import sys
import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
import pandas as pd
import zipfile
import pathlib
import tempfile
import os
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse     # ← NEW
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
# Import core logic from service modules
from BedrijfLocatiecodering.bedrijfscodering import bedrijfscodering as proc_bedrijf
from BedrijfLocatiecodering.locatiecodering import locatiecodering as proc_locatie
from BedrijfLocatiecodering.sharepoint import fetch_bedrijf_df, fetch_locatie_df
from Plantion.Plantion import clean_gln_to_xls 

from GPC import export_code_lists, load_to_postgres
from Bio_Certificaat import main as certificate
from APIData import strategy_direct_json
from Financieel.omzet import main

# ─── FASTAPI SETUP ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Floricode",
    description="Floricode automatiseringen en Dashboard",
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

@app.get("/health", tags=["Health"])
def health_check():
    logger.info("Health check invoked")
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# ─── AUTOMATIONS ────────────────────────────────────────────────────────────
@app.post("/import/import-excel", tags=["Automations"])
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

@app.post("/access/run-access", tags=["Automations"])
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

@app.post("/biocertificate/scraper", tags=["Automations"])
def api_run_biocertificate():
    debug_steps = []
    try:
        debug_steps.append("Starting Data-Extraction ")
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
        outfile=certificate()                    # returns Path or str
        path=str(outfile)
        filename=Path(outfile).name

    except Exception as e:
        error_msg = str(e)
        debug_steps.append(f"Error occurred: {error_msg}")
        logger.error(f"Data-Extraction pipeline failed: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail={"error": error_msg, "debug": debug_steps}
        )

    return FileResponse(
        path=str(outfile),
        filename=Path(outfile).name,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={f"Content-Disposition": f'attachment; filename="{filename}"'}
    )
            
@app.post("/bedrijflocatie/rfh", tags=["Automations"])
def download_coderingen():
            # 1) run jouw bestaande logica
    df_loc = fetch_locatie_df()   
    df_bedrijf = fetch_bedrijf_df()
    if df_bedrijf is None or df_loc is None:
        raise HTTPException(404, "Geen data gevonden voor bedrijf of locatie")

    try:
        # 2️⃣  Data verwerken → DataFrames
        bedrijf_df             = proc_bedrijf(df_bedrijf)   # DataFrame
        locatie1_df, locatie2_df = proc_locatie(df_loc)     # twee DataFrames

        # 3️⃣  Zip opbouwen in geheugen
        mem_zip = BytesIO()
        with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            # helper om DF als Excel-bytes te schrijven
            def add_df_to_zip(df, name: str):
                buf = BytesIO()
                df.to_excel(buf, index=False, engine="openpyxl")
                buf.seek(0)
                zf.writestr(name, buf.read())

            add_df_to_zip(bedrijf_df,  "bedrijfscodering.xls")
            add_df_to_zip(locatie1_df, "locatiecodering_in.xls")
            add_df_to_zip(locatie2_df, "locatiecodering_uit.xls")

        mem_zip.seek(0)


    except Exception as exc:
        logging.exception("Coderingen genereren mislukte")
        raise HTTPException(500, f"Fout: {exc}")

    # 4️⃣  Zip streamen naar de browser
    headers = {"Content-Disposition": 'attachment; filename="coderingen.zip"'}
    return StreamingResponse(mem_zip, media_type="application/zip", headers=headers)

@app.post("/bedrijflocatie/plantion", tags=["Automations"])
def api_run_plantion():
    try:
        df = clean_gln_to_xls()               # DataFrame

        # 1️⃣  schrijf DF naar geheugen-buffer
        buf = BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")  # of "xlwt" voor .xls
        buf.seek(0)                         # reset pointer

    except Exception as exc:
        logging.exception("Plantion export mislukte")
        raise HTTPException(500, f"Fout: {exc}")

    # 2️⃣  stuur exact die buffer terug
    headers = {"Content-Disposition": 'attachment; filename="Plantion.xls"'}
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
@app.get("/omzet/data", tags=["Automations"])
def get_omzet_data():
    data=main()
          # NaN → None, types → JSON-safe
    return data 
# ─── Uvicorn LAUNCH (DEV ONLY) ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
