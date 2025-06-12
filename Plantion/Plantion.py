# gln_clean_to_xls.py
# --------------------------------------------------------------
from pathlib import Path
import re, pandas as pd
from Plantion.Outlook import fetch_mail_data
from datetime import datetime
date = datetime.now().strftime("%Y-%m-%d")
file=fetch_mail_data()
def explode_two_header_rows(df: pd.DataFrame) -> pd.DataFrame:

    # 1) Identify blob-column and any meta-columns
    blob_header = df.columns[0]
    meta_cols = list(df.columns[1:]) 
    df.loc[-1] = [blob_header] + df.iloc[0, 1:].tolist()  # insert at index -1
    df.index = df.index + 1   # shift everything down by 1
    df = df.sort_index()      # now row 0 is your blob

    # 3) reset columns so pandas gives you generic names
    df.columns = range(df.shape[1])

    raw1 = str(df.iloc[0, 0]).rstrip(';')
    raw2 = str(df.iloc[1, 0]).rstrip(';')

    # 2) Build your header list
    header1 = [h.strip() for h in raw1.split(';')]
    header2 = [h.strip() for h in raw2.split(';')]
    final_header = header1 + header2

    print(final_header)
    n_header = len(final_header)
    # 4) Take every row *after* the first two as the real data
    # 2) Isolate only the data rows (everything after row 1)
    data_blob = df.iloc[2:, 0].reset_index(drop=True)

    # 3) Split into columns, pad or trim to match n_header
    expanded = data_blob.str.split(';', expand=True)

    # 3a) If too few cols, add empty ones
    if expanded.shape[1] < n_header:
        for i in range(expanded.shape[1], n_header):
            expanded[i] = ""            # new column full of empty strings

    # 3b) If too many cols, just drop the extras
    expanded = expanded.iloc[:, :n_header]

    # 4) Assign your real column names
    expanded.columns = final_header

    # 5) Re-attach any trailing meta columns
    if meta_cols:
        meta_df = df.iloc[2:, 1:].reset_index(drop=True)
        expanded = pd.concat([expanded, meta_df], axis=1)

    return expanded


# ── 2. VBA-equivalent cleaner ─────────────────────────────────
def process_gln_dataframe(df: pd.DataFrame):
    print(df)

    df = df.copy()
    df=explode_two_header_rows(df)
    macro_cols = [
        "postal_identification_code", "city_name", "country_name_code",
        "GLN_company_address_code", "GLN_company_address_code_organisation",
        "entry_date", "expiry_date", "change_date_time", "request_date_time",
        "record_ID", "Sector_code", "country_prod_code",
        "coc_branch_number", "phytosanitary_registration_number",
    ]
    for c in macro_cols:
        if c not in df.columns:
            df[c] = pd.NA

    df.loc[df["GLN_code_requester"].str.strip().ne(""), "Sector_code"] = 1
    df["country_prod_code"] = df["country_name_code"]

    for c in ("GLN_code_requester", "change_date_time", "request_date_time"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    filled = df["expiry_date"].fillna("").str.strip().str.lower().ne("")
    removed = df.loc[filled, "Plantion_registration_nr"].tolist()
    return df.loc[~filled].reset_index(drop=True), removed

# ── 3. one-liner: csv → cleaned df → .xls ─────────────────────
def clean_gln_to_xls():
    
    df_clean, removed = process_gln_dataframe(file)

    # xlwt is the engine pandas uses for .xls; install if missing:  pip install xlwt
    if df_clean.shape[0] > 65535:
        raise ValueError("'.xls' format can hold max 65 535 rows; file is larger.")

    print("⚠️  Rows removed due to expiry_date:", ", ".join(removed))
    return df_clean


# ─── quick demo ───
if __name__ == "__main__":
    
    df_final = clean_gln_to_xls()
