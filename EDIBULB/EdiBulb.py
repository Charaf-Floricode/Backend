from xlwt import Workbook
import os
from datetime import datetime
from EDIBULB.Outlook import edibulb
import pandas as pd

def verwerk_meerdere_mutatiebestanden(*dataframes, uitvoerpad=None):


    gewenste_kolommen = [
        "Code_list_id", "GLN", "Bedrijfsnaam", "xxx_registration_nr", "yyy_registration_number", "zzz_registration_number",
        "company_level_code", "company_role_code", "entry_date", "expire_date", "change_date_time",
        "GLN_company_addres_code_organisation", "KvK", "Alternatieve naam/handelsnaam",
        "Straat", "Huisnr", "Toevoeging", "Postcode", "Plaats", "Landcode", "Status", "Opmerking"
    ]

    def niet_leeg(waarde):
        return isinstance(waarde, str) and waarde.strip() != ""

    # Combineer dataframes
    samengevoegd = pd.concat(dataframes, ignore_index=True)

    # Vul ontbrekende kolommen aan
    for col in gewenste_kolommen:
        if col not in samengevoegd.columns:
            samengevoegd[col] = ""

    # Verwerk relevante logica
    samengevoegd['company_level_code'] = samengevoegd['Bedrijfsnaam'].apply(lambda x: "2" if niet_leeg(x) else "")
    samengevoegd['company_role_code'] = samengevoegd['Bedrijfsnaam'].apply(lambda x: "O" if niet_leeg(x) else "")

    # Alleen juiste kolommen behouden
    resultaat = samengevoegd[gewenste_kolommen].copy()

    # Verwijder lege rijen (zonder Bedrijfsnaam)
    resultaat = resultaat[resultaat['Bedrijfsnaam'].apply(niet_leeg)]
    if resultaat["Postcode"].fillna("").eq("").all():
        resultaat["Postcode"] = 0
    if resultaat["Straat"].fillna("").eq("").all():
        resultaat["Straat"] = 0

    resultaat['KvK'] = resultaat['KvK'].fillna('').astype(str)
    lens = resultaat['KvK'].str.len()
    mask = (lens < 8) & (lens > 1)
    #mask = resultaat['KvK'].str.len() < 8 and resultaat['KvK'].str.len() > 1
    resultaat.loc[mask, 'KvK'] = '0' + resultaat.loc[mask, 'KvK']
    # Export naar .xls
    wb = Workbook()
    ws = wb.add_sheet("Mutaties")
    for col_idx, col in enumerate(gewenste_kolommen):
        ws.write(0, col_idx, col)
    for row_idx, row in resultaat.iterrows():
        for col_idx, value in enumerate(row):
            ws.write(row_idx + 1, col_idx, value)

    bestandsnaam = f"Import_EDIBulb_{datetime.today().strftime('%Y%m%d')}.xls"
    if uitvoerpad is None:
        uitvoerpad = os.getcwd()
    pad = os.path.join(uitvoerpad, bestandsnaam)
    wb.save(pad)

    print(f"✅ Bestand opgeslagen als: {pad}")
    return resultaat


def main():
    dataframes = edibulb()  # Dit is een lijst van dataframes
    resultaat = verwerk_meerdere_mutatiebestanden(*dataframes)  # Let op de ster * hier

    print(resultaat)
    return resultaat