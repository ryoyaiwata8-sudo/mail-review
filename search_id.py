
import pandas as pd
import os

data_dir = r"c:\Users\ryoya\.gemini\antigravity\playground\thermal-coronal\data"
search_id = "M0122420"
files = [
    "再見積もり依頼_9JUN_3PM.xlsx",
    "質問_9JUN_3PM.xlsx"
]

print(f"Searching for {search_id} in email logs...")

for f in files:
    path = os.path.join(data_dir, f)
    try:
        df = pd.read_excel(path)
        # Search in all columns
        mask = df.apply(lambda x: x.astype(str).str.contains(search_id, case=False, na=False)).any(axis=1)
        if mask.any():
            print(f"Found {search_id} in {f}!")
            print(df[mask].to_string())
        else:
            print(f"Not found in {f}")
    except Exception as e:
        print(f"Error reading {f}: {e}")
