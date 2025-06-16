# mega_helpers.py ────────────────────────────────────────────
from mega.mega import Mega
import os, pandas as pd
from io import BytesIO
import tempfile
from dotenv import load_dotenv
load_dotenv()
mega = Mega()

def main():
    mega = Mega()
    m = mega.login(os.getenv("MEGA_EMAIL"),
    os.getenv("MEGA_PASS"))
    path_in_cloud="Floricode/Omzetoverzicht contracten 2025 incl verlengingen.xlsx"
    file = m.find(path_in_cloud)
    if file is None:
        raise FileNotFoundError("Bestand niet gevonden in Mega")

    # 1️⃣  download to memory (no disk needed)
    data = m.download(file, dest_path=None)  # returns bytes

    # 2️⃣  read into pandas
    df = pd.read_excel(data)
    return df
