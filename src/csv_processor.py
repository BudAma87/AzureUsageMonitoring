
import pandas as pd
import os

def load_csv(file_path: str) -> pd.DataFrame:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV not found: {file_path}")
    df = pd.read_csv(file_path)
    return df

def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    # Basic cleaning and summarization
    df = df.dropna(how='all')  # remove completely empty rows
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    return df.describe(include='all')
