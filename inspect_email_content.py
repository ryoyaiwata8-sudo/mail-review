
import pandas as pd
import os

data_dir = r"c:\Users\ryoya\.gemini\antigravity\playground\thermal-coronal\data"
files = [
    "再見積もり依頼_9JUN_3PM.xlsx",
    "質問_9JUN_3PM.xlsx"
]

for f in files:
    path = os.path.join(data_dir, f)
    print(f"--- {f} ---")
    try:
        df = pd.read_excel(path, nrows=5)
        print(df[['件名', '本文', '担当者']].to_string())
    except Exception as e:
        print(f"Error reading {f}: {e}")
    print("\n")
