import os, msal, requests, base64
from io import BytesIO
import pandas as pd
from dotenv import load_dotenv
from bedrijfscodering import bedrijfscodering
from locatiecodering import locatiecodering
load_dotenv()
TENANT_ID     = os.getenv("sTENANT_ID")
CLIENT_ID     = os.getenv("sCLIENT_ID")
CLIENT_SECRET = os.getenv("sCLIENT_SECRET")

HOSTNAME = "floricode.sharepoint.com"
SITE_PATH = "/sites/FloricodebeheerLocatie-enBedrijfscoderingen"
RFH_DRIVE_ID = "b!hPEDF6HaRECiiQPkHpx6AoLsZi6g6ZdLlkFx15UGhcsatvagk_vUSqPeSQOcF5Wb"   # uit je lijst

GRAPH   = "https://graph.microsoft.com/v1.0"
AUTH    = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE   = ["https://graph.microsoft.com/.default"]

def get_token() -> str:
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTH, client_credential=CLIENT_SECRET
    )
    tok = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in tok:
        raise RuntimeError(tok)
    return tok["access_token"]

def load_first_file_as_df() -> pd.DataFrame | None:
    """Download het eerste CSV of XLSX in RFH & return als DataFrame."""
    headers = {"Authorization": f"Bearer {get_token()}"}

    # 1️⃣ lijst top-level items en eventuele submappen
    queue = [f"{GRAPH}/drives/{RFH_DRIVE_ID}/root/children"]
    visited_folders = set()

    while queue:
        url = queue.pop(0)
        data = requests.get(url, headers=headers, timeout=30).json()

        for itm in data.get("value", []):
            if "file" in itm:                         # bestand gevonden
                name = itm["name"]
                ext  = name.rsplit(".",1)[-1].lower()

                if ext not in ("csv", "xlsx", "xls"):
                    continue  # sla niet-CSV/XLSX over

                # 2️⃣ download & lees in DataFrame
                raw = requests.get(
                    f"{GRAPH}/drives/{RFH_DRIVE_ID}/items/{itm['id']}/content",
                    headers=headers, timeout=30
                ).content

                bio = BytesIO(raw)
                if ext == "csv":
                    df = pd.read_csv(bio, encoding="utf-8")
                else:  # xlsx / xls
                    # neem eerste sheet
                    df = pd.read_excel(bio, engine="openpyxl")

                print(f"Gevonden & geladen: {name}")
                return df

            # als het een map is: voeg children-endpoint toe aan queue
            if "folder" in itm:
                fid = itm["id"]
                if fid not in visited_folders:
                    visited_folders.add(fid)
                    queue.append(f"{GRAPH}/drives/{RFH_DRIVE_ID}/items/{fid}/children")

        # volg paginatie
        if "@odata.nextLink" in data:
            queue.append(data["@odata.nextLink"])

    print("Geen CSV/XLSX gevonden in RFH.")
    return None


# -------- voorbeeldgebruik -------------------------------------------------
if __name__ == "__main__":
    df = load_first_file_as_df()
    if df is not None:
        print(df.head())
