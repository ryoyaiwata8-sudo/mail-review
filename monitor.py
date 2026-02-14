
import os
import time
import json
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

from src.data_ingestion import DataIngestion
from src.case_linking import CaseLinker
from src.evaluator import Evaluator, GeminiLLMClient, OpenAILLMClient, MockLLMClient
from src.audio_processor import AudioProcessor

DASHBOARD_JSON = "dashboard_data.json"

class NewFileHandler(FileSystemEventHandler):
    def __init__(self, evaluator, audio_processor, data_ingestion, case_linker):
        self.evaluator = evaluator
        self.audio_processor = audio_processor
        self.data_ingestion = data_ingestion
        self.case_linker = case_linker
        self.processing = False

    def on_created(self, event):
        if event.is_directory:
            return
        filename = os.path.basename(event.src_path)
        if filename.endswith((".mp3", ".xlsx")):
            print(f"\n[NEW FILE DETECTED] {filename}")
            self.process_latest()

    def on_modified(self, event):
        # Excel files trigger modified multiple times
        if event.is_directory:
            return
        filename = os.path.basename(event.src_path)
        if filename.endswith(".xlsx"):
            print(f"\n[EXCEL UPDATED] {filename}")
            self.process_latest()

    def process_latest(self):
        if self.processing:
            return
        self.processing = True
        try:
            time.sleep(1) # Wait for file lock to release
            print("Re-scanning data directory...")
            interactions = self.data_ingestion.load_all()
            cases = self.case_linker.link_cases(interactions)
            
            if not cases:
                print("No cases found.")
                return

            # Pick the case with the newest interaction
            latest_case = max(cases, key=lambda c: max(i.timestamp for i in c.interactions))
            print(f"Latest activity detected for agent: {latest_case.agent} ({latest_case.case_id})")

            # Transcription if needed
            for interaction in latest_case.interactions:
                if interaction.type == "PHONE" and interaction.file_path and not interaction.body:
                    print(f"Transcribing {os.path.basename(interaction.file_path)}...")
                    interaction.body = self.audio_processor.transcribe(interaction.file_path)

            print("Evaluating...")
            result = self.evaluator.evaluate_case(latest_case)
            
            # Save to dashboard JSON
            self.update_dashboard_json(result)
            print(f"Evaluation complete for {latest_case.agent}. Dashboard updated.")

        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            self.processing = False

    def update_dashboard_json(self, result):
        data = []
        if os.path.exists(DASHBOARD_JSON):
            with open(DASHBOARD_JSON, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except:
                    data = []
        
        # Add timestamp and append
        result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data.insert(0, result) # Newest first
        
        # Keep only last 50
        data = data[:50]
        
        with open(DASHBOARD_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    load_dotenv()
    # Use robust path resolution
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.getenv("DATA_DIR", os.path.join(current_dir, "data"))
    if not os.path.exists(data_dir):
        print(f"Error: Directory not found: {data_dir}")
        return
    
    print(f"--- Starting Real-time Monitor ---")
    print(f"Target Directory: {data_dir}")

    gemini_key = os.getenv("GEMINI_API_KEY")
    provider = os.getenv("MODEL_PROVIDER", "gemini").lower()

    if gemini_key:
        print("Using Gemini API for Real-time Evaluation")
        llm_client = GeminiLLMClient(gemini_key)
        audio_processor = AudioProcessor(provider="gemini", api_key=gemini_key)
    else:
        print("Warning: No Gemini API key. Using Mock.")
        llm_client = MockLLMClient()
        audio_processor = None

    data_ingestion = DataIngestion(data_dir)
    case_linker = CaseLinker()
    evaluator = Evaluator(llm_client)

    event_handler = NewFileHandler(evaluator, audio_processor, data_ingestion, case_linker)
    observer = Observer()
    observer.schedule(event_handler, data_dir, recursive=False)
    
    print(f"Watcher started on: {data_dir}")
    print("Evaluating existing files once on startup...")
    event_handler.process_latest()
    
    print("\nEntering event loop. Add a file to /data to trigger AI analysis.")
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
