import pandas as pd
import os


def locatiecodering(df):
    
    df_in = df[df['expiry_date'].isna()]           # Actieve locaties (zonder einddatum)
    df_out = df[df['expiry_date'].notna()]         # Vervallen locaties (met einddatum)
    return df_in, df_out