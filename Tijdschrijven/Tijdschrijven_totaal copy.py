#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
lees_tijdschrijven_rapport.py
─────────────────────────────
• zoekt de laagste (laatste) kopregel 'Taak'
• vult samengevoegde lege cellen (Taak / Klant / Project / Afdeling) met ffill
• rekent kolom 'Duur' om naar decimale uren
• toont snelle totalen
"""

import math
import datetime as dt
from pathlib import Path
from Tijdschrijven.file import main
import pandas as pd
from openpyxl import load_workbook

# ---------------------------------------------------------------- SETTINGS

SHEET_NAME = "Rapport"
# -------------------------------------------------------------------------


def to_hours(x) -> float:
    """ Zet tijd / duur → float-uren. """
    if x is None or x == "" or (isinstance(x, float) and math.isnan(x)):
        return math.nan
    if isinstance(x, (dt.timedelta, pd.Timedelta)):
        return x.total_seconds() / 3600
    if isinstance(x, dt.time):
        return x.hour + x.minute / 60 + x.second / 3600
    if isinstance(x, dt.datetime):  # Excel-waarde > 24u
        days = x.day - 1
        return days * 24 + x.hour + x.minute / 60 + x.second / 3600
    if isinstance(x, str):
        try:
            return pd.to_timedelta(x).total_seconds() / 3600
        except Exception:
            pass
    return math.nan


def load_hours() -> pd.DataFrame:
    file=main()
    # ── 3. DataFrame + ffill op samengevoegde kolommen ───────────────────
    newfile=pd.DataFrame(file)
    df = newfile

    # ── 4. uren toevoegen ────────────────────────────────────────────────
    df["Uren"] = df["Duur"].apply(to_hours)
    return df

def main_tijd():
    df = load_hours()

    # Top-taken
    uren_per_taak = (
        df.groupby("Taak", as_index=False)["Uren"]
        .sum()
        .sort_values("Uren", ascending=False)
    )
    return uren_per_taak


