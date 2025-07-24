import os
import msal
import requests
import base64
from io import BytesIO
import pandas as pd
from fnmatch import fnmatch
from dotenv import load_dotenv

load_dotenv()
"""
Connect to Microsoft Graph, pull emails from a specific folder,
filter on sender/keywords, download Excel/CSV attachments,
flatten into one DataFrame with metadata columns, and return it.
"""
# --- Configuration ---
TENANT_ID         = os.getenv("TENANT_ID")
CLIENT_ID         = os.getenv("CLIENT_ID")
CLIENT_SECRET     = os.getenv("CLIENT_SECRET")
SHARED_MAILBOX    = "codebeheer@floricode.com"
BUSINESS_FOLDER_ID = (
    "AQMkADkwNjQ4OTJjLTYyZGEtNGVmMi1iZjRjLTEwZjBlNGE5NmU3MQAuAAAD"
    "oqtNvUomHUGUI-e9nUb1wAEAMX-QDi0j6EySstfjbtSumQAFPuKP9AAAAA=="
)
PLANTION=(
    "AQMkADkwNjQ4OTJjLTYyZGEtNGVmMi1iZjRjLTEwZjBlNGE5NmU3MQAuAAADoqtNvUomHUGUI-e9nUb1wAEAMX-QDi0j6EySstfjbtSumQAHS_RBogAAAA=="
)
EDIBULB=(
    "AQMkADkwNjQ4OTJjLTYyZGEtNGVmMi1iZjRjLTEwZjBlNGE5NmU3MQAuAAADoqtNvUomHUGUI-e9nUb1wAEAMX-QDi0j6EySstfjbtSumQAHU47E3QAAAA=="
)
# Criteria
SENDERS           = {"info@plantion.nl"}
SENDERS_EDIBULB           = {"IVBadmin@hobaho.nl","administratie@cnb.nl"}
KEYWORDS          = ["Mutatie GLN codes naar FloriCode"]

ATT_NAME_PATTERNS = ["*.xlsx", "*.csv", "GLNPLE*"]

# Graph setup
AUTHORITY  = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE      = ["https://graph.microsoft.com/.default"]
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

# 1) Acquire token
app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET
)
token_res = app.acquire_token_for_client(scopes=SCOPE)
access_token = token_res.get("access_token")
if not access_token:
    raise RuntimeError(f"Failed to acquire token: {token_res}")

headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept":        "application/json"
}

#alle folders checken
subs = requests.get(
f"https://graph.microsoft.com/v1.0/users/{SHARED_MAILBOX}/mailFolders/AQMkADkwNjQ4OTJjLTYyZGEtNGVmMi1iZjRjLTEwZjBlNGE5NmU3MQAuAAADoqtNvUomHUGUI-e9nUb1wAEAMX-QDi0j6EySstfjbtSumQAAAWvovgAAAA==/childFolders",
headers=headers).json()
#print(subs)
def edibulb():
    url_msgs = (
        f"{GRAPH_ROOT}/users/{SHARED_MAILBOX}"
        f"/mailFolders/{EDIBULB}/messages"
        "?$top=2"
        "&$orderby=receivedDateTime desc"
        "&$select=id,receivedDateTime,from,subject,bodyPreview,hasAttachments"
    )
    resp = requests.get(url_msgs, headers=headers)
    resp.raise_for_status()
    messages = resp.json().get("value", [])

        # 3) Filter in Python on sender and keywords in subject/bodyPreview
    senders_lc = {s.lower() for s in SENDERS_EDIBULB}
    messages = [
        m for m in messages
        if m["from"]["emailAddress"]["address"].lower() in senders_lc
    ]

    if not messages:
        print("Geen berichten van opgegeven afzenders.")
        return []

    results = []   # list of dicts: {'df': DataFrame, 'msg': m, 'att_name': name}

    # 3. loop over elk bericht
    for m in messages:
        if not m["hasAttachments"]:
            continue

        # download ALLE bijlagen van dit bericht
        atts = requests.get(
            f"{GRAPH_ROOT}/users/{SHARED_MAILBOX}"
            f"/mailFolders/{EDIBULB}/messages/{m['id']}/attachments",
            headers=headers).json()["value"]

        for att in atts:
            name = att["name"]
            ext  = name.split(".")[-1].lower()
            if ext not in {"csv", "xlsx", "xls"}:
                continue   # sla niet-CSV/Excel over

            raw = base64.b64decode(att["contentBytes"])
            bio = BytesIO(raw)
            df  = (pd.read_csv(bio, encoding="utf-8")
                   if ext == "csv"
                   else pd.read_excel(bio, engine="openpyxl", sheet_name="Mutaties"))

            df = df.dropna(how="all").dropna(how="all", axis=1)
            results.append({
                "df":        df,
                "msg":       m,
                "att_name":  name,
            })
            print(f"· attachment '{name}' uit '{m['subject']}' geladen → {df.shape}")
            print(df)
    return [r["df"] for r in results]


