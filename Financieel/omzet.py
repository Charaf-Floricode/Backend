# routes/omzet.py  ─────────────────────────────────────────────
from fastapi import APIRouter, HTTPException
import pandas as pd, numpy as np
from pathlib import Path
from datetime import datetime


def main():
    SOURCE = Path(r"C:\Users\c.elkhattabi\Downloads\Omzetoverzicht contracten 2025 incl verlengingen.xlsx")
    if not SOURCE.exists():
        raise HTTPException(404, "Bron-Excel niet gevonden")

    df = pd.read_excel(SOURCE)

    # ---------- 1. Aantal abonnementen per land ----------
    land_counts = (
        df["Landcode"]
        .value_counts(dropna=False)
        .sort_index()
        .to_dict()
    )

    # ---------- 2. Top-10 diensten ----------
    dienst_counts = (
        df["Naam dienst"]
        .value_counts()
        .head(10)
        .to_dict()
    )

    # ---------- 3. Histogram bins netto prijs ----------
    hist, bin_edges = np.histogram(df["Netto prijs"].dropna(), bins=30)
    hist_data = {
        "bins": bin_edges.round(2).tolist(),
        "freq": hist.tolist(),
    }

    # ---------- 4. Boxplot data per dienst (≥15) ----------
    top_diensten = df["Naam dienst"].value_counts()
    top_diensten = top_diensten[top_diensten >= 15].index
    boxplot = {
        dienst: df.loc[df["Naam dienst"] == dienst, "Netto prijs"]
                    .dropna()
                    .tolist()
        for dienst in top_diensten
    }

    # ---------- 5. Nieuwe per maand ----------
    start = pd.to_datetime(df["Startdatum"])
    per_month = (
        start.dt.to_period("M")
              .astype(str)
              .value_counts()
              .sort_index()
              .to_dict()
    )

    # ---------- 6. Totale netto prijs per relatietype ----------
    df["Relatietype_lower"] = df["Relatietype"].str.lower().str.strip()
    totaal_rel = (
        df.groupby("Relatietype_lower")["Netto prijs"]
          .sum()
          .reindex(["kweker", "handelaar", "softwareleverancier"])
          .fillna(0)
          .to_dict()
    )
    totaal_rel["kweker"] += 400_000   # business-regel

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "land_counts": land_counts,           # { NL: 123, DE: 42, … }
        "dienst_counts": dienst_counts,       # { 'Service A': 80, … }
        "histogram": hist_data,               # { bins: [...], freq: [...] }
        "boxplot": boxplot,                   # { 'Service A': [..prices..] }
        "nieuw_per_maand": per_month,         # { '2025-01': 12, … }
        "totaal_per_relatietype": totaal_rel, # { kweker: xxxx, … }
    }
