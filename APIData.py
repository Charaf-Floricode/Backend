import pandas as pd
import requests
import json
from collections import defaultdict
from openai import OpenAI
import os
import time
from datetime import date

from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

"""
florecompc2        FP (1)    Product /VBN/Product
florecompc2      FT (3)     Gewas  /VBN/Plant
florecompc2      FG (4)    Geslacht              /VBN/Genus
florecompc2      FS (5)     Soort     /VBN/Species
florecompc2      FC (6)    Cultivar /VBN/Cultivar
florecompc2      FN (13) Benaming           /VBN/Name
florecompc2      FM (14) Benamingstype /VBN/NameType
florecompc2      FO (16) Groep   /VBN/ProductGroup
FLC020101	C33	BRICK	/FLC/GpcBrick
FLC020101	C36	SEGMENT_FAMILY_CLASS_BRICK	/FLC/GpcHierarchy
FLC020101	C37	BRICK_ATTRIBUTE_TYPE_ATTRIBUTE_VALUE	/FLC/GpcBrickAttribute
FLC020101	C39	PRODUCT_GPC	/FLC/GpcBrickToProduct

        
 
"""
""""
     "Benaming/Name", "CN??????.txt"
     "Benamingstype/NameType", "CM??????.txt"
     "Cultivar", "CC??????.txt"
     "Geslacht/Genus", "CG??????.txt"
     "Gewas/Plant", "CT??????.txt"
     "Groep/ProductGroup", "CO??????.txt"
     "Kenmerkgroep/FeatureGroup", "CU??????.txt"
     "Kenmerktype/FeatureType", "CE??????.txt"
     "Kenmerkwaarde/FeautureValue", "CV??????.txt"
     "Product", "CP??????.txt"
     "Productkenmerk/ProductFeature", "CF??????.txt"
     "Regl. Kenmerktype/RegulatoryFeatureType", "CY??????.txt"
     "Soort/Species", "CS??????.txt"
     "Toepassing/Application", "CA??????.txt"
     "Voorschrift type/RegulationType", "CR??????.txt"

"""


# Strategie 1: Batch techniek met AI
import pandas as pd
import requests
import json
from openai import OpenAI
import os
import time

def get_access_token():
    link    = 'https://api.floricode.com/oauth/token'
    CLIENT_ID     = 'ProdFloricode'
    CLIENT_SECRET = 'eHsQEBbV7KBM2JFabFWz'
    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    resp = requests.post(link, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    resp.raise_for_status()
    return resp.json()['access_token']


def api_call_all(endpoint, page_size=1000):
    token   = get_access_token()
    headers = {'Authorization': f'Bearer {token}'}
    all_vals = []
    skip      = 0
    while True:
        url  = f'https://api.floricode.com/v2{endpoint}?$top={page_size}&$skip={skip}'
        r    = requests.get(url, headers=headers)
        r.raise_for_status()
        js   = r.json()
        vals = js.get('value', [])
        all_vals.extend(vals)
        if len(vals) < page_size:
            break
        skip += page_size
    return all_vals



def split_batches(records: list, batch_size: int = 200):
    for i in range(0, len(records), batch_size):
        yield records[i:i+batch_size]




def strategy_direct_json():
    endpoints = [
        '/VBN/Language',
        '/VBN/RegulationType',
        '/VBN/RegulatoryFeatureType',
        '/VBN/FeatureGroup',
        '/VBN/FeatureValue',
        '/VBN/FeatureType',
        '/VBN/ProductFeature',
        '/VBN/Application',
        '/VBN/Product',
        '/VBN/Plant', 
        '/VBN/Genus', 
        '/VBN/Species', 
        '/VBN/Cultivar', 
        '/VBN/Name', 
        '/VBN/NameType',
        '/VBN/ProductGroup'

    ]
    prefix_map = {
        '/VBN/Name': 'CN',
        '/VBN/NameType': 'CM',
        '/VBN/Cultivar': 'CC',
        '/VBN/Genus': 'CG',
        '/VBN/Plant': 'CT',
        '/VBN/ProductGroup': 'CO',
        '/VBN/FeatureGroup': 'CU',
        '/VBN/FeatureType': 'CE',
        '/VBN/FeatureValue': 'CV',
        '/VBN/Product': 'CP',
        '/VBN/ProductFeature': 'CF',
        '/VBN/RegulatoryFeatureType': 'CY',
        '/VBN/Species': 'CS',
        '/VBN/Application': 'CA',
        '/VBN/RegulationType': 'CR',
        '/VBN/Language': 'CL'
    }
    today = date.today().strftime("%Y%m%d")

    for ep in endpoints:
        records = api_call_all(ep)
        df = pd.json_normalize(records)
        prefix = prefix_map.get(ep)
        if not prefix:
            raise KeyError(f"Geen prefix mapping voor endpoint {ep}")
        out = f"C:/Users/Floricode/Desktop/GPC code/Data/{prefix}{today}.txt"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        df.to_csv(out, index=False)
        print(f"[Direct JSON] {len(df)} rijen weggeschreven naar {out}")


if __name__ == '__main__':
    # kies welke strategie je wilt draaien:
    #strategy_batch_ai()
    strategy_direct_json()
