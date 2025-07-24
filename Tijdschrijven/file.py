from mega.mega import Mega
import os, pandas as pd
from io import BytesIO
import tempfile
from dotenv import load_dotenv
load_dotenv()
mega = Mega()
m = mega.login(os.getenv("MEGA_EMAIL"),
os.getenv("MEGA_PASS"))
def main():

    path_in_cloud="Floricode/Rapport 2025-07-23 13-22-44 (1).xlsx"
    file = m.find(path_in_cloud)
    if file is None:
        raise FileNotFoundError("Bestand niet gevonden in Mega")

    # 1️⃣  download to memory (no disk needed)
    data = m.download(file, dest_path=None)  # returns bytes

    # 2️⃣  read into pandas
    df = pd.read_excel(data)
    return df
