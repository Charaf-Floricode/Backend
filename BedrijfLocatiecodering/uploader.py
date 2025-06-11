# uploader.py
import os, io, requests, msal
import importlib

from BedrijfLocatiecodering.sharepoint import fetch_bedrijf_df, fetch_locatie_df, DRIVE_RF
from BedrijfLocatiecodering.bedrijfscodering import bedrijfscodering as proc_bedrijf
from BedrijfLocatiecodering.locatiecodering import locatiecodering as proc_locatie


import pandas as pd, datetime as dt
from dotenv import load_dotenv
load_dotenv()
today = dt.datetime.today().strftime("%Y%m%d")
TENANT_ID  = os.getenv("sTENANT_ID")
CLIENT_ID  = os.getenv("sCLIENT_ID")
CLIENT_SECRET = os.getenv("sCLIENT_SECRET")
GRAPH = "https://graph.microsoft.com/v1.0"
SCOPE   = ["https://graph.microsoft.com/.default"]
AUTH    = f"https://login.microsoftonline.com/{TENANT_ID}"
def _token() -> str:
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTH, client_credential=CLIENT_SECRET
    )
    tok = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in tok:
        raise RuntimeError(tok)
    return tok["access_token"]

HEAD = {"Authorization": f"Bearer {_token()}"}

def upload_xlsx(drive_id: str, folder_id: str, filename: str, bytes_io: io.BytesIO):
    url = f"{GRAPH}/drives/{drive_id}/items/{folder_id}:/{filename}:/content"
    resp = requests.put(url, headers=HEAD, data=bytes_io.getvalue())
    resp.raise_for_status()

df_bedrijf = fetch_bedrijf_df()
if df_bedrijf is not None:
    out = proc_bedrijf(df_bedrijf)
    bio = io.BytesIO(); out.to_excel(bio, index=False); bio.seek(0)
    upload_xlsx(DRIVE_RF, out_folder_id := df_bedrijf.attrs.get("parent_id"),
                f"mutaties_bedrijfscoderingen_{today}.xlsx", bio)
    print("Bedrijfscodering geüpload.")

# ── Locatiecodering ──────────────────
df_loc = fetch_locatie_df()
if df_loc is not None:
    df_in, df_out = proc_locatie(df_loc)
    for tag, df_part in [("in", df_in), ("uit", df_out)]:
        bio = io.BytesIO(); df_part.to_excel(bio, index=False); bio.seek(0)
        upload_xlsx(DRIVE_RF, out_folder_id := df_loc.attrs.get("parent_id"),
                    f"mutaties_locatiecoderingen_{today}_{tag}.xlsx", bio)
    print("Locatiecodering geüpload.")