import pandas as pd
import os
import re

def validate_lengths_and_types(df: pd.DataFrame):
    """Raise if any column breaks its (TypeCode, MaxLen) rule."""
    rules = {
        'Sector_code':                          ('N', 1),
        'GLN_code_requester':                   ('N',13),
        'FH_registration_nr':                   ('N', 7),
        'FHA_registration_nr':                  ('N', 7),
        'Plantion_registration_nr':             ('N', 8),
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

def locatiecodering(df):
    if df["postal_identification_code"].fillna("").eq("").all():
        df["postal_identification_code"] = 0
    if df["street_number"].fillna("").eq("").all():
        df["street_number"] = 0

    errors=validate_lengths_and_types(df)
    
    df_in = df[df['expiry_date'].isna()]           # Actieve locaties (zonder einddatum)
    df_out = df[df['expiry_date'].notna()]   
          # Vervallen locaties (met einddatum)
    return df_in, df_out, errors