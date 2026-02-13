
import pandas as pd
import os

data_dir = r"c:\Users\ryoya\.gemini\antigravity\playground\thermal-coronal\data"
f = "（旧）電話応対評価シート.xlsx"
path = os.path.join(data_dir, f)

try:
    df = pd.read_excel(path, header=None, nrows=20)
    print(df.to_string())
except Exception as e:
    print(f"Error: {e}")
