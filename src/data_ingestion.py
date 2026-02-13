
import os
import pandas as pd
import re
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Interaction:
    id: str
    type: str  # 'EMAIL' or 'PHONE'
    timestamp: datetime
    agent: str
    customer_key: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    file_path: Optional[str] = None
    raw_data: Optional[dict] = None

class DataIngestion:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        # Expanded agent map based on observation
        self.agent_map = {
            "HAMASAKI": "濱﨑彩那",
            "YUMOTO": "湯本",
            "濱崎": "濱﨑彩那", # Normalize to full name if possible
            # Add more as discovered
        }

    def normalize_agent(self, name: str) -> str:
        if not isinstance(name, str) or pd.isna(name):
            return "Unknown"
        name = name.strip()
        # Direct map check
        if name.upper() in self.agent_map:
            return self.agent_map[name.upper()]
        
        # Partial match check (e.g. if map has "濱﨑" and input is "濱﨑彩那", maybe we want the longer one?)
        # For now, just return as is if not in map, but maybe handle "崎" vs "﨑"
        name = name.replace("崎", "﨑") # Standardize Kanji
        return name

    def load_audio_logs(self) -> List[Interaction]:
        interactions = []
        # Pattern: Mxxxxxx_Topic_Agent.mp3
        pattern = re.compile(r"(M\d+)_(.+)_(.+)\.mp3")
        
        for f in os.listdir(self.data_dir):
            if f.endswith(".mp3"):
                match = pattern.match(f)
                if match:
                    case_id, topic, agent_raw = match.groups()
                    file_path = os.path.join(self.data_dir, f)
                    timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    interaction = Interaction(
                        id=case_id, 
                        type="PHONE",
                        timestamp=timestamp,
                        agent=self.normalize_agent(agent_raw),
                        subject=topic,
                        file_path=file_path,
                        raw_data={"filename": f}
                    )
                    interactions.append(interaction)
        return interactions

    def load_email_logs(self) -> List[Interaction]:
        interactions = []
        for f in os.listdir(self.data_dir):
            if f.endswith(".xlsx") and ("タスク管理" not in f) and ("レポート" not in f) and ("評価" not in f) and ("チェック" not in f):
                path = os.path.join(self.data_dir, f)
                try:
                    df = pd.read_excel(path)
                    
                    for _, row in df.iterrows():
                        # Handle ID
                        email_id_raw = row.get('メール番号', '')
                        if pd.isna(email_id_raw) or str(email_id_raw).lower() == 'nan' or str(email_id_raw).strip() == '':
                             email_id = f"EMAIL_{hash(str(row))}" # Fallback
                        else:
                             email_id = str(int(float(email_id_raw))) if isinstance(email_id_raw, (int, float)) else str(email_id_raw)

                        # Parse timestamp
                        ts_raw = row.get('日時')
                        timestamp = ts_raw if isinstance(ts_raw, datetime) else datetime.now() # Fallback
                        
                        agent = self.normalize_agent(row.get('担当者', ''))
                        subject = str(row.get('件名', '')) if not pd.isna(row.get('件名')) else ""
                        body = str(row.get('本文', '')) if not pd.isna(row.get('本文')) else ""
                        sender = str(row.get('差出人', '')) if not pd.isna(row.get('差出人')) else ""
                        
                        interaction = Interaction(
                            id=email_id,
                            type="EMAIL",
                            timestamp=timestamp,
                            agent=agent,
                            customer_key=sender, 
                            subject=subject,
                            body=body,
                            file_path=path,
                            raw_data=row.to_dict()
                        )
                        interactions.append(interaction)

                except Exception as e:
                    print(f"Error loading email log {f}: {e}")
                    
        return interactions

    def load_all(self) -> List[Interaction]:
        return self.load_audio_logs() + self.load_email_logs()
