import os
import msal
import requests
import base64
from io import BytesIO
import pandas as pd
from fnmatch import fnmatch
from dotenv import load_dotenv

load_dotenv()

def fetch_mail_data() -> pd.DataFrame:
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

    # Criteria
    SENDERS           = {"info@plantion.nl"}
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

    # 2) Fetch messages from the business folder
    url_msgs = (
        f"{GRAPH_ROOT}/users/{SHARED_MAILBOX}"
        f"/mailFolders/{PLANTION}/messages"
        "?$top=1"
        "&$orderby=receivedDateTime desc"
        "&$select=id,receivedDateTime,from,subject,bodyPreview,hasAttachments"
    )
    resp = requests.get(url_msgs, headers=headers)
    resp.raise_for_status()
    messages = resp.json().get("value", [])

    # 3) Filter in Python on sender and keywords in subject/bodyPreview
    def matches(msg):
        addr = msg["from"]["emailAddress"]["address"].lower()
        if SENDERS and addr not in SENDERS:
            return False
        subj = msg["subject"].lower()
        body = (msg.get("bodyPreview") or "").lower()
        return any(kw.lower() in subj or kw.lower() in body for kw in KEYWORDS)

    filtered = [m for m in messages if matches(m)]

    # 4) Download & parse attachments into a master list of DataFrames
# 4) Download & parse attachments into a master list of DataFrames
    pieces = []
    found_glnple = False       # <-- vlag

    for m in filtered:         # messages staan al newest-first
        if found_glnple:
            break              # we hebben ’m al, klaar

        msg_id  = m["id"]
        subject = m["subject"]

        if not m["hasAttachments"]:
            continue

        url_atts = (
            f"{GRAPH_ROOT}/users/{SHARED_MAILBOX}"
            f"/mailFolders/{BUSINESS_FOLDER_ID}/messages/{msg_id}/attachments"
        )
        r2 = requests.get(url_atts, headers=headers)
        r2.raise_for_status()

        for att in r2.json().get("value", []):
            name = att["name"]
            if not fnmatch(name.lower(), "glnple*"):     # preciezere test
                continue

            # ------------ attachment voldoet, nu verwerken ------------
            raw = base64.b64decode(att["contentBytes"])
            ext = name.rsplit(".", 1)[-1].lower()
            bio = BytesIO(raw)

            if ext in ("xlsx", "xls"):
                sheets = pd.read_excel(bio, sheet_name=None, engine="openpyxl")
                for sheet_name, df in sheets.items():
                    dfc = df.dropna(how="all").dropna(how="all", axis=1)
                    if dfc.empty:
                        continue
                    pieces.append(dfc)                   # geen metadata nodig?
            elif ext == "csv":
                df = pd.read_csv(bio, encoding="utf-8")
                dfc = df.dropna(how="all").dropna(how="all", axis=1)
                if not dfc.empty:
                    pieces.append(dfc)

            found_glnple = True                         # <-- zet vlag
            break                                       # geen andere attachments uit dit mailtje meer nodig


    # 5) Concatenate all pieces into one DataFrame
    if pieces:
        master_df = pd.concat(pieces, ignore_index=True)
    else:
        master_df = pd.DataFrame()

    return master_df

def main():
    df = fetch_mail_data()
    df_clean = df.loc[:, ~df.columns.str.startswith("__")]
    df_clean.to_csv(r"C:\Users\Floricode\Downloads\GLNPLE.csv", sep='\t', index=False)

# or, explicitly
# df_clean = df.drop(columns=["__msg_id", "__subject", "__att_name", "__sheet_name"])

    #print(df_clean)
    return df_clean

if __name__ == "__main__":
    main()