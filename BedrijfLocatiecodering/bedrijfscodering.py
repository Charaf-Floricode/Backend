import pandas as pd
import os
from datetime import datetime
import re
# === Huidige datum voor bestandsnamen ===
today_str = datetime.today().strftime('%Y%m%d')
def validate_lengths_and_types(df: pd.DataFrame):
    """Raise if any column breaks its (TypeCode, MaxLen) rule."""
    rules = {
        'Sector_code':                          ('N', 1),
        'GLN_code_requester':                   ('N',13),
        'chamber_registration_number':          ('N', 8),
        'coc_branch_number':                    ('N',12),
        'phytosanitary_registration_number':    ('N',10),
        'company_role_code':                    ('A', 1),
        'company_location_level_code':          ('N', 1),
        'company_name':                         ('AN',70),
        'alternative_company_name':             ('AN',70),
        'street_name':                          ('AN',35),
        'street_number':                        ('AN', 9),
        'street_number_suffix':                 ('AN', 6),
        'postal_identification_code':           ('AN', 9),
        'city_name':                            ('AN',35),
        'country_name_code':                    ('AN', 3),
        'country_prod_code':                    ('AN', 3),
        'GLN_company_address_code_organisation':('N',13),
        'entry_date':                           ('N', 8),
        'expiry_date':                          ('N', 8),
        'change_date_time':                     ('N',12),
        'request_date_time':                    ('N',12),
    }
    tests = {
        'N':  lambda v: bool(re.fullmatch(r'\d*', v)),
        'A':  lambda v: bool(re.fullmatch(r'[A-Za-z]*', v)),
        'AN': lambda v: bool(re.fullmatch(r'[A-Za-z0-9]*', v)),
    }
    errors = []
    for col, (ctype, maxlen) in rules.items():
        if col not in df.columns:
            continue
        series = (
            df[col]
              .fillna('')
              .astype(str)
             .str.replace(r'\.0$', '', regex=True)
       )
        for idx, val in series.items():
            if len(val) > maxlen:
                errors.append(f"{col}[row {idx}]: length {len(val)} > {maxlen}")
            if ctype in ('N','A') and not tests[ctype](val):
                errors.append(f"{col}[row {idx}]: invalid ({ctype}): '{val}'")
    return errors


# Bedrijfscodering en locatiecodering script automatisering met dataframe als input:
def bedrijfscodering(df):
    # CONTROLE 1: Puntkomma's
    semicolon_issues = df.applymap(lambda x: isinstance(x, str) and ';' in x)
    semicolon_cells = semicolon_issues.stack()[lambda x: x].index.tolist()

    # CONTROLE 2: Verplichte velden bij ingevulde GLN_code
    missing_fields = []
    for idx, row in df.iterrows():
        if pd.notna(row['GLN_company_address_code']):
            if pd.isna(row['street_name']):
                missing_fields.append((idx + 2, 'street_name'))
            if pd.isna(row['street_number']):
                missing_fields.append((idx + 2, 'street_number'))
            if pd.isna(row['postal_identification_code']):
                missing_fields.append((idx + 2, 'postal_identification_code'))
            if pd.isna(row['city_name']):
                missing_fields.append((idx + 2, 'city_name'))

    # CONTROLE 3: KvK-nummer moet 8 cijfers
    kvk_issues = []
    for idx, kvk in enumerate(df['chamber_registration_number'], start=2):
        if pd.notna(kvk):
            kvk_str = str(kvk).strip()
            if (kvk_str.isdigit() and len(kvk_str) == 8):
                kvk_issues.append((idx, kvk_str))

    # CONTROLE 4: Dubbele FH_registration_nr
    fh_dupes = df[df.duplicated(subset=['FH_registration_nr'], keep=False)]

    # Bewerking: Sector_code toevoegen
    df['Sector_code'] = 1

    # Bewerking: FH_registration_nr en expiry_date leegmaken
    mask = df['expiry_date'].notna()
    df.loc[mask, 'FH_registration_nr'] = pd.NA
    df.loc[mask, 'expiry_date'] = pd.NA

    print(f"Bedrijvenbestand verwerkt")
    if semicolon_cells:
        print(f"Puntkomma's gevonden in cellen: {semicolon_cells}")
    if missing_fields:
        print(f"Ontbrekende verplichte velden: {missing_fields}")
    if kvk_issues:
        print(f"KvK-nummer fouten: {kvk_issues}")
    if not fh_dupes.empty:
        print(f"Dubbele FH_registration_nr gevonden:\n{fh_dupes[['FH_registration_nr']].to_string(index=False)}")
    if not (semicolon_cells or missing_fields or kvk_issues or not fh_dupes.empty):
        print("Geen fouten gevonden!")
    errors=validate_lengths_and_types(df)
    return df, errors