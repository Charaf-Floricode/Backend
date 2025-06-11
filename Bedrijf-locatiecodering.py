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