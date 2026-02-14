
import os
from datetime import datetime, date
from dotenv import load_dotenv
from src.data_ingestion import DataIngestion
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
    
    linker = CaseLinker()
    cases = linker.link_cases(interactions)
    print(f"Total Cases Found: {len(cases)}")

    # === Step 2: Sampling Readiness (Pre-transcription for Gating) ===
    sampler = Sampler()
    in_range_cases, _ = sampler.split_by_period(cases, start_date, end_date)
    
    if audio_processor:
        print("Pre-transcribing in-range calls for gating...")
        for case in in_range_cases:
            for interaction in case.interactions:
                if interaction.type == "PHONE" and interaction.file_path and not interaction.body:
                    print(f"  Gating check transcript: {os.path.basename(interaction.file_path)}...")
                    # For gating, we just need text.
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

    # === Step 5: Final Export ===
    print("\nExporting Phase 6 results...")
    eval_only = [r for r in final_results if r["status"] == "evaluated"]
    if eval_only:
        export_phase5(eval_only)
        export_to_excel_phase5(eval_only, "weekly_check_sheet.xlsx")

    # Generate Markdown Reports (Dual output: Score and Coach)
    reporter_score = Reporter(mode="score")
    report_score = reporter_score.generate_report(final_results, start_date, end_date)
    with open("score_report.md", "w", encoding="utf-8") as f:
        f.write(report_score)

    reporter_coach = Reporter(mode="coach")
    report_coach = reporter_coach.generate_report(final_results, start_date, end_date)
    with open("coach_report.md", "w", encoding="utf-8") as f:
        f.write(report_coach)
    
    # Also keep weekly_report.md as a default (Score mode)
    with open("weekly_report.md", "w", encoding="utf-8") as f:
        f.write(report_score)
    
    print("Phase 6 complete. Reports generated: score_report.md, coach_report.md, and weekly_report.md.")


if __name__ == "__main__":
    main()
