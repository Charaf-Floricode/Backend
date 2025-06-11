# fetcher.py
import os, msal, requests, io, re, pandas as pd
from dotenv import load_dotenv
import datetime as dt
load_dotenv()
today = dt.datetime.today().strftime("%Y%m%d")
TENANT_ID  = os.getenv("sTENANT_ID")
CLIENT_ID  = os.getenv("sCLIENT_ID")
CLIENT_SECRET = os.getenv("sCLIENT_SECRET")
HOSTNAME   = "floricode.sharepoint.com"
SITE_PATH  = "/sites/FloricodebeheerLocatie-enBedrijfscoderingen"
DRIVE_RF   = "b!hPEDF6HaRECiiQPkHpx6AoLsZi6g6ZdLlkFx15UGhcsatvagk_vUSqPeSQOcF5Wb"
DRIVE_PL   = "b!hPEDF6HaRECiiQPkHpx6AoLsZi6g6ZdLlkFx15UGhcvavI6I8vABTIAo6UmmyAEj"
GRAPH      = "https://graph.microsoft.com/v1.0"
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

def _latest_item(drive_id, pattern: str):
    """Return item-json van het nieuwste bestand dat op `pattern` matcht."""
    q = f"{GRAPH}/drives/{drive_id}/root/children?$orderby=lastModifiedDateTime desc"
    while q:
        data = requests.get(q, headers=HEAD).json()
        for it in data.get("value", []):
            if "file" in it and re.search(pattern, it["name"], re.I):
                return it
            if "@odata.nextLink" in data:
                q = data["@odata.nextLink"]
        q = None
    return None

def download_as_df(item):
    raw = requests.get(f"{GRAPH}/drives/{item['parentReference']['driveId']}/items/{item['id']}/content",
                       headers=HEAD).content
    ext = item["name"].split(".")[-1].lower()
    bio = io.BytesIO(raw)
    df = pd.read_excel(bio, engine="openpyxl")  # of read_csv
    # ← Bewaar de map-id in de DataFrame-attributen
    df.attrs["parent_id"] = item["parentReference"]["id"]
    print(df.attrs)
    df.attrs["drive_id"]  = item["parentReference"]["driveId"]
    return df

# ---------- publieks-API ---------------------------------------------------
def fetch_bedrijf_df():
    today = dt.datetime.today().strftime("%Y%m%d")
    itm   = _latest_item(DRIVE_RF, rf"bedrijfscoderingen_{today}\.")   # match exact vandaag
    return download_as_df(itm) if itm else None

def fetch_locatie_df():
    today = dt.datetime.today().strftime("%Y%m%d")
    itm   = _latest_item(DRIVE_RF, rf"locatiecoderingen_{today}\.")  # match exact vandaag
    return download_as_df(itm) if itm else None