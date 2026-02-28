
import os
from datetime import datetime, date
from dotenv import load_dotenv
import pandas as pd
from src.data_ingestion import DataIngestion, Interaction
from src.case_linking import CaseLinker
from src.sampler import Sampler
from src.evaluator import Evaluator, GeminiLLMClient
from src.reporter import Reporter
from src.audio_processor import AudioProcessor
from src.exporter import export_phase5, export_to_excel_phase5


def parse_date(s: str, default: date) -> date:
    """Parse YYYY-MM-DD string to date, or return default."""
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return default


def main():
    load_dotenv()

    data_dir = os.getenv("DATA_DIR", r"c:\Users\ryoya\.gemini\antigravity\playground\thermal-coronal\data")

    print("--- Starting Weekly Report System (Phase 6: Hold Time & Dual-Sample) ---")

    # === Configure Target Period ===
    today = date(2026, 2, 14) 
    weekday = today.weekday()
    default_start = today.replace(day=today.day - weekday)
    default_end = today

    start_date = parse_date(os.getenv("TARGET_START_DATE", ""), default_start)
    end_date = parse_date(os.getenv("TARGET_END_DATE", ""), default_end)
    print(f"Target Period: {start_date} ~ {end_date}")

    # === API Configuration ===
    gemini_key = os.getenv("GEMINI_API_KEY")
    llm_client = GeminiLLMClient(gemini_key) if gemini_key else None
    audio_processor = AudioProcessor(provider="gemini", api_key=gemini_key) if gemini_key else None

    if not llm_client:
        print("Error: Gemini API Key missing.")
        return

    # === Step 1: Data Load & Linking ===
    print("Loading data...")
    ingestion = DataIngestion(data_dir)
    interactions = ingestion.load_all()
    
    # Load specific file requested by user
    extra_file = r"C:\Users\ryoya\Documents\intern\vexum\トラベルスタンダード\電話・対応\質問_9JUN_3PM.xlsx"
    if os.path.exists(extra_file):
        print(f"Loading extra file: {extra_file}")
        try:
            extra_df = pd.read_excel(extra_file)
            for _, row in extra_df.iterrows():
                # Simple conversion to Interaction
                i = Interaction(
                    id=f"EXTRA_{row.get('メール番号', hash(str(row)))}",
                    type="EMAIL",
                    timestamp=row.get('日時', datetime.now()),
                    agent=ingestion.normalize_agent(row.get('担当者', '')),
                    subject=str(row.get('件名', '')),
                    body=str(row.get('本文', '')),
                    file_path=extra_file,
                    raw_data=row.to_dict()
                )
                interactions.append(i)
        except Exception as e:
            print(f"Failed to load extra file: {e}")

    linker = CaseLinker()
    cases = linker.link_cases(interactions)
    
    # === Agent Filtering ===
    target_agents = ["小杉勇太", "湯本", "内藤結衣", "小杉", "内藤", "湯元"]
    cases = [c for c in cases if any(a in c.agent for a in target_agents)]
    print(f"Total Cases Found for target agents: {len(cases)}")

    # === Step 2: Sampling Readiness ===
    # Relax period for this specific run if the file is from June
    if "9JUN" in extra_file:
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 30)
        print(f"Adjusted Target Period for extra file data: {start_date} ~ {end_date}")

    sampler = Sampler()
    in_range_cases, _ = sampler.split_by_period(cases, start_date, end_date)
    
    if audio_processor:
        print("Pre-transcribing in-range calls for gating...")
        for case in in_range_cases:
            for interaction in case.interactions:
                if interaction.type == "PHONE" and interaction.file_path and not interaction.body:
                    print(f"  Gating check transcript: {os.path.basename(interaction.file_path)}...")
                    interaction.body = audio_processor.transcribe(interaction.file_path)

    # === Step 3: Phase 6 Selection (EMAILx1 + CALLx1) ===
    print("Selecting dual samples per agent (EMAILx1 + CALLx1)...")
    selection_bundles = sampler.select_samples_phase6(in_range_cases, cases, start_date, end_date)
    
    # === Step 4: Evaluation Orchestration ===
    evaluator = Evaluator(llm_client)
    final_results = []

    for bundle in selection_bundles:
        agent = bundle["agent"]
        print(f"\n[AGENT: {agent}]")

        for channel in ["CALL", "EMAIL"]:
            key = "call_case" if channel == "CALL" else "email_case"
            entry = bundle[key]
            
            if entry["status"] == "selected":
                case = entry["case"]
                print(f"  Evaluating {channel}: {case.case_id} ({entry['fallback'] or 'strict'})")
                
                hold_sec = 0
                hold_segments = []
                info = {}
                # If Call, get Hold Time
                if channel == "CALL" and audio_processor:
                    for interaction in case.interactions:
                        if interaction.type == "PHONE" and interaction.file_path:
                            # Use process_full for rich info
                            info = audio_processor.process_full(interaction.file_path)
                            interaction.body = info.get("text")
                            hold_sec += info.get("hold_total_sec", 0)
                            hold_segments.extend(info.get("hold_segments", []))

                # Evaluate
                result = evaluator.evaluate_case(case)
                result["hold_total_sec"] = hold_sec
                result["total_duration_sec"] = info.get("total_duration_sec", 0) if channel == "CALL" else 0
                result["hold_segments"] = hold_segments
                result["fallback"] = entry["fallback"] or "strict"
                final_results.append(result)
            else:
                print(f"  Skipping {channel}: {entry['reason']}")
                # Add a stub result for reporting
                final_results.append({
                    "agent": agent,
                    "channel": channel,
                    "status": "skipped",
                    "reason": entry["reason"]
                })

    # === Final Export ===
    import json
    import time
    print("\nExporting results...")
    
    # Backup results to JSON
    with open("last_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)
    
    eval_only = [r for r in final_results if r["status"] == "evaluated"]
    if eval_only:
        try:
            export_phase5(eval_only, call_path="CHECK_LOG_CALL.csv", email_path="CHECK_LOG_EMAIL.csv")
            print("Export complete: CHECK_LOG_CALL.csv, CHECK_LOG_EMAIL.csv")
        except PermissionError:
            ts = time.strftime("%Y%m%d_%H%M%S")
            alt_call = f"CHECK_LOG_CALL_{ts}.csv"
            alt_email = f"CHECK_LOG_EMAIL_{ts}.csv"
            print(f"Warning: Primary files locked. Saving to {alt_call} and {alt_email}")
            export_phase5(eval_only, call_path=alt_call, email_path=alt_email)
        except Exception as e:
            print(f"Export failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("No cases were evaluated. No CSV generated.")


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        print("\n--- ERROR TRACEBACK ---")
        traceback.print_exc()
        print("-----------------------")
