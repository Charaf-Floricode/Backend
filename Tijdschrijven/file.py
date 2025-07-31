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

    path_in_cloud="Floricode/Rapport 2025-07-31 11-02-11.xlsx"
    file = m.find(path_in_cloud)
    if file is None:
        raise FileNotFoundError("Bestand niet gevonden in Mega")

    # 1️⃣  download to memory (no disk needed)
    data = m.download(file, dest_path=None)  # returns bytes
    
    # 2️⃣  read into pandas
    df = pd.read_excel(data,skiprows=8)
    for col in df.columns:
        if 'Unnamed' in col:
            df.rename(columns={col: df.loc[0, col]}, inplace=True)
    df = df.drop(0, axis=0).reset_index(drop=True)
    print(df)
    return df

