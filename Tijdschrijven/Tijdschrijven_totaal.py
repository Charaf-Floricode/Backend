# tijdschrijven.py
from __future__ import annotations
import math
import datetime as dt
from typing import Dict, List, Optional

import pandas as pd
from Tijdschrijven.file import main as load_file  # levert records of DataFrame

SHEET_NAME = "Rapport"

# -- helpers ---------------------------------------------------------------

def to_hours(x) -> float:
    if x is None or x == "" or (isinstance(x, float) and math.isnan(x)):
        return math.nan
    if isinstance(x, (dt.timedelta, pd.Timedelta)):
        return x.total_seconds() / 3600
    if isinstance(x, dt.time):
        return x.hour + x.minute / 60 + x.second / 3600
    if isinstance(x, dt.datetime):
        days = x.day - 1
        return days * 24 + x.hour + x.minute / 60 + x.second / 3600
    if isinstance(x, str):
        try:
            return pd.to_timedelta(x).total_seconds() / 3600
        except Exception:
            pass
    return math.nan

def _person_col(df: pd.DataFrame) -> Optional[str]:
    for c in ["Persoon", "Medewerker", "Naam", "User", "Gebruiker"]:
        if c in df.columns:
            return c
    return None

def _mask_contains(df: pd.DataFrame, col: str, patterns: List[str]) -> pd.Series:
    s = df[col].astype(str)
    m = pd.Series(False, index=df.index)
    for p in patterns:
        m = m | s.str.contains(p, case=False, na=False)
    return m

def _per_person(df: pd.DataFrame, person_col: Optional[str]) -> List[Dict[str, float]]:
    if not person_col or df.empty:
        return []
    tmp = (
        df.groupby(person_col, as_index=False)["Uren"].sum()
          .rename(columns={person_col: "name", "Uren": "hours"})
          .sort_values("hours", ascending=False)
    )
    return tmp.to_dict(orient="records")

def _color_from_pct(pct: float) -> str:
    if pct is None:
        return "groen"
    if pct < 3.0:   # drempels naar wens
        return "groen"
    if pct < 5.0:
        return "oranje"
    return "rood"

def _color_from_beheer(beheer_uren: float) -> str:
    if beheer_uren < 200:
        return "groen"
    if beheer_uren < 300:
        return "oranje"
    return "rood"

# -- data laden ------------------------------------------------------------

def load_hours() -> pd.DataFrame:
    """
    Haal het tijdschrijven-rapport op en reken 'Duur' om naar float 'Uren'.
    Verwacht kolommen: Taak, Duur, (optioneel) Persoon/Medewerker/…
    """
    if load_file is None:
        raise RuntimeError("Loader (Tijdschrijven.file.main) niet gevonden")

    raw = load_file()  # jouw bestaande helper – lijst dicts of DataFrame
    df = pd.DataFrame(raw) if not isinstance(raw, pd.DataFrame) else raw.copy()

    if "Duur" not in df.columns:
        raise ValueError("Kolom 'Duur' ontbreekt in het rapport")

    df["Uren"] = df["Duur"].apply(to_hours)
    return df

def main_tijd() -> pd.DataFrame:
    """Totale uren per taak (zoals je al had)."""
    df = load_hours()
    uren_per_taak = (
        df.groupby("Taak", as_index=False)["Uren"]
          .sum()
          .sort_values("Uren", ascending=False)
    )
    return uren_per_taak

# -- hoofdaggregatie voor /intern/status -----------------------------------

def build_intern_status() -> Dict:
    """
    Berekent de payload voor het /intern/status endpoint.
    Geeft een dict terug met keys: color, per_task, sick_hours, sick_pct, panels.
    """
    df = load_hours()
    if df.empty:
        return {
            "color": "groen",
            "per_task": {},
            "sick_hours": 0.0,
            "sick_pct": 0.0,
            "panels": [],
        }

    if "Taak" not in df.columns:
        raise ValueError("Kolom 'Taak' ontbreekt in dataset")

    total_hours = float(df["Uren"].sum())
    person_col  = _person_col(df)

    # categorie-maskers (pas trefwoorden aan als nodig)
    m_sick     = _mask_contains(df, "Taak", ["ziek"])
    m_leave    = _mask_contains(df, "Taak", ["verlof"])
    m_overtime = _mask_contains(df, "Taak", ["overuren", "overwerk"])

    sick_hours  = float(df.loc[m_sick, "Uren"].sum())
    leave_hours = float(df.loc[m_leave, "Uren"].sum())
    over_hours  = float(df.loc[m_overtime, "Uren"].sum())

    sick_pct = round((sick_hours / total_hours * 100), 2) if total_hours > 0 else 0.0

    # per taak
    per_task = (
        df.groupby("Taak", as_index=False)["Uren"]
          .sum()
          .sort_values("Uren", ascending=False)
          .set_index("Taak")["Uren"]
          .round(2)
          .to_dict()
    )

    # kleur voor HOME-tegel Intern (op basis van beheer-uren, pas aan naar KPI)
    beheer_uren = float(per_task.get("Beheer", 0.0))
    color_home  = _color_from_beheer(beheer_uren)

    # panelen (incl. per-persoon tabellen)
    panels = [
        {
            "key": "ziekteverzuim",
            "label": "Ziekteverzuim",
            "color": _color_from_pct(sick_pct),
            "total_hours": round(sick_hours, 2),
            "sick_pct": sick_pct,                             # FE toont % in header
            "per_person": _per_person(df.loc[m_sick], person_col),
        },
        {
            "key": "verlof",
            "label": "Verlof",
            "color": "groen",
            "total_hours": round(leave_hours, 2),
            "per_person": _per_person(df.loc[m_leave], person_col),
        },
        {
            "key": "overuren",
            "label": "Overuren",
            "color": "oranje",
            "total_hours": round(over_hours, 2),
            "per_person": _per_person(df.loc[m_overtime], person_col),
        },
        {
            "key": "per_persoon_totaal",
            "label": "Uren per persoon (totaal)",
            "color": "groen",
            "total_hours": round(total_hours, 2),
            "per_person": _per_person(df, person_col),
        },
        {
            "key": "totale_uren_per_taak",
            "label": "Totale uren per taak",
            "color": "groen",
            "total_hours": round(total_hours, 2),
            # tabel komt uit root.per_task in FE
        },
    ]

    return {
        "color": color_home,
        "per_task": per_task,
        "sick_hours": round(sick_hours, 2),
        "sick_pct": sick_pct,
        "panels": panels,
    }
