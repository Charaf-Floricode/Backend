# gln_clean_to_xls.py
# --------------------------------------------------------------
from pathlib import Path
import re, pandas as pd
from Plantion.Outlook import fetch_mail_data
from datetime import datetime
from io import StringIO

date = datetime.now().strftime("%Y-%m-%d")

def explode_two_header_rows(raw: bytes, encoding="utf-8") -> pd.DataFrame:
    """
    raw: the exact bytes you pasted (with \r\n separators)
    returns: a DataFrame whose columns are the 22 header fields,
             and whose rows are the data lines.
    """
    # 1) Turn bytes into a cleaned-up text block
    text = raw.decode(encoding, errors="replace")
    # Normalize line endings and split
    lines = [line for line in text.replace("\r\n", "\n").split("\n") if line]

    if len(lines) < 3:
        raise ValueError("Expected at least 3 lines: 2 headers + data.")

    # 2) Build your final header from the *first two* lines
    header1 = lines[0].rstrip(";").split(";")
    header2 = lines[1].rstrip(";").split(";")
    final_header = [h.strip() for h in header1 + header2]
    
    # 3) Read the remaining lines into a mini-CSV (semicolon-delimited)
    data_text = "\n".join(lines[2:]) + "\n"
    #print(data_text)
    df = pd.read_csv(
        StringIO(data_text),
        sep=";", header=None, names=final_header,
        dtype=str, keep_default_na=False, engine="python"
    )
    print(df)

    # 4) Pad or trim rows so every row has exactly len(final_header) columns
    n = len(final_header)
    def pad(row):
        if len(row) < n:
            return row + [""]*(n - len(row))
        else:
            return row[:n]

    # split each line manually to ensure consistent columns
    rows = [pad(r.rstrip(";").split(";")) for r in lines[2:]]
    df = pd.DataFrame(rows, columns=final_header, dtype=str)

    return df

from decimal import Decimal

def excel_sci_to_int(s: str) -> str:
    # turn the Excel‐style "8,71378E+12" into a Python Decimal, then to int
    # 1) normalize comma→dot, strip out any spaces
    s_norm = s.strip().replace(",", ".").replace(" ", "")
    try:
        dec = Decimal(s_norm)
        # convert to int, then back to string
        return str(int(dec))
    except:
        return s 

def validate_lengths_and_types(df: pd.DataFrame):
    """Raise if any column breaks its (TypeCode, MaxLen) rule."""
    rules = {
        'Sector_code':                          ('N', 1),
        'Record_ID':                            ('N', 3),
        'GLN_code_requester':                   ('N',13),
        'FH_registration_nr':                   ('N', 7),
        'FHA_registration_nr':                  ('N', 7),
        'Plantion_registration_nr':             ('N', 8),
        'chamber_registration_number':          ('N', 8),
        'coc_branch_number':                    ('N',12),
        'phytosanitary_registration_number':    ('N',10),
        'company_role_code':                    ('A', 1),
        'company_location_level_code':          ('N', 1),
        'company_name':                         ('AN',70),
        'alternative_company_name':             ('AN',70),
        'street_name':                          ('AN',35),
        'street_number':                        ('AN', 9),
        'street_number_suffix':                 ('AN', 6),
        'postal_identification_code':           ('AN', 9),
        'city_name':                            ('AN',35),
        'country_name_code':                    ('AN', 3),
        'country_prod_code':                    ('AN', 3),
        'GLN_company_address_code':             ('N',13),
        'GLN_company_address_code_organisation':('N',13),
        'entry_date':                           ('N', 8),
        'expiry_date':                          ('N', 8),
        'change_date_time':                     ('N',12),
        'request_date_time':                    ('N',12),
    }
    tests = {
        'N':  lambda v: bool(re.fullmatch(r'\d*', v)),
        'A':  lambda v: bool(re.fullmatch(r'[A-Za-z]*', v)),
        'AN': lambda v: bool(re.fullmatch(r'[A-Za-z0-9]*', v)),
    }
    errors = []
    for col, (ctype, maxlen) in rules.items():
        if col not in df.columns:
            continue
        series = df[col].fillna('').astype(str)
        for idx, val in series.items():
            if len(val) > maxlen:
                errors.append(f"{col}[row {idx}]: length {len(val)} > {maxlen}")
            if ctype in ('N','A') and not tests[ctype](val):
                errors.append(f"{col}[row {idx}]: invalid ({ctype}): '{val}'")

    return errors
# ── 2. VBA-equivalent cleaner ─────────────────────────────────
def process_gln_dataframe(df: pd.DataFrame):
    
    
    df=explode_two_header_rows(df)
    print(df)
    macro_cols = [
        "postal_identification_code", "city_name", "country_name_code",
        "GLN_company_address_code", "GLN_company_address_code_organisation",
        "entry_date", "expiry_date", "change_date_time", "request_date_time",
        "record_ID", "Sector_code", "country_prod_code",
        "coc_branch_number", "phytosanitary_registration_number",
    ]
    for c in ("GLN_code_requester", "change_date_time", "request_date_time"):
        if c in df.columns:
         df[c] = df[c].apply(excel_sci_to_int)
    for c in macro_cols:
        if c not in df.columns:
            df[c] = pd.NA

    df.loc[df["GLN_code_requester"].str.strip().ne(""), "Sector_code"] = 1
    df["country_prod_code"] = df["country_name_code"]

    if df["postal_identification_code"].fillna("").eq("").all():
        df["postal_identification_code"] = 0
    if df["street_number"].fillna("").eq("").all():
        df["street_number"] = 0

    df['chamber_registration_number'] = df['chamber_registration_number'].fillna('').astype(str)
    lens = df['chamber_registration_number'].str.len()
    mask = (lens < 8) & (lens > 1)
    df.loc[mask, 'chamber_registration_number'] = '0' + df.loc[mask, 'chamber_registration_number'] 

    filled = df["expiry_date"].fillna("").str.strip().str.lower().ne("")
    removed = df.loc[filled, "Plantion_registration_nr"].tolist()
    errors=validate_lengths_and_types(df)
    return df.loc[~filled].reset_index(drop=True), removed, errors

# ── 3. one-liner: csv → cleaned df → .xls ─────────────────────
def clean_gln_to_xls():
    file=fetch_mail_data()
    df_clean, removed, errors = process_gln_dataframe(file)
    print(df_clean)
    df_clean.to_csv(r"C:\Users\c.elkhattabi\Downloads\df.csv", sep=";", index=False)
    # xlwt is the engine pandas uses for .xls; install if missing:  pip install xlwt
    if df_clean.shape[0] > 65535:
        raise ValueError("'.xls' format can hold max 65 535 rows; file is larger.")

    print("⚠️  Rows removed due to expiry_date:", ", ".join(removed))
    return df_clean, removed, errors


# ─── quick demo ───
if __name__ == "__main__":
    
    df_final = clean_gln_to_xls()
