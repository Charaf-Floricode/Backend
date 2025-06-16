# routes/omzet.py ────────────────────────────────────────────
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from Financieel.file import main as megafile

def main():
    

    df = pd.read_excel(megafile())

    # 1️⃣ Aantal abonnementen per land
    land_counts = (
        df["Landcode"]
        .fillna("onbekend")            # ← eerst vullen …
        .value_counts()
        .sort_index()
        .to_dict()
    )

    # 2️⃣ Top-10 diensten
    dienst_counts = (
        df["Naam dienst"]
        .value_counts()
        .head(10)
        .to_dict()
    )

    # 3️⃣ Histogram netto prijs
    hist, bins = np.histogram(df["Netto prijs"].dropna(), bins=30)
    hist_data = {
        "bins": bins.round(2).tolist(),
        "freq": hist.astype(int).tolist(),
    }

    # 4️⃣ Boxplot per dienst (≥15)
    top = df["Naam dienst"].value_counts()
    top = top[top >= 15].index
    boxplot = {
        dienst: df.loc[df["Naam dienst"] == dienst, "Netto prijs"]
                   .dropna()
                   .tolist()
        for dienst in top
    }

    # 5️⃣ Nieuwe abonnementen per maand
    start = pd.to_datetime(df["Startdatum"])
    per_month = (
        start.dt.to_period("M")
              .astype(str)
              .value_counts()
              .sort_index()
              .to_dict()
    )

    # 6️⃣ Totale netto prijs per relatietype
    df["Relatietype_lower"] = df["Relatietype"].str.lower().str.strip()
    totaal_rel = (
        df.groupby("Relatietype_lower")["Netto prijs"]
          .sum()
          .reindex(["kweker", "handelaar", "softwareleverancier"])
          .fillna(0)
          .to_dict()
    )
    totaal_rel["kweker"] += 400_000  # business-regel

    return jsonable_encoder({          # ← zet NaN → None e.d.
        "generated_at": datetime.utcnow().isoformat(),
        "land_counts": land_counts,
        "dienst_counts": dienst_counts,
        "histogram": hist_data,
        "boxplot": boxplot,
        "nieuw_per_maand": per_month,
        "totaal_per_relatietype": totaal_rel,
    })
