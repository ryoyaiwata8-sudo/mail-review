
import os
import pandas as pd

print("Script started")
data_dir = r"c:\Users\ryoya\Documents\intern\vexum\トラベルスタンダード\電話・対応" # Trying the original path first? No, use the copied one.
data_dir = r"c:\Users\ryoya\.gemini\antigravity\playground\thermal-coronal\data"

if not os.path.exists(data_dir):
    print(f"Directory not found: {data_dir}")
else:
    print(f"Directory found: {data_dir}")
    files = os.listdir(data_dir)
    print(f"Files: {files}")
    
    for f in files:
        if f.endswith(".xlsx"):
            path = os.path.join(data_dir, f)
            print(f"Reading {f}...")
            try:
                df = pd.read_excel(path, nrows=1)
                print(f"Columns: {df.columns.tolist()}")
            except Exception as e:
                print(f"Error: {e}")
