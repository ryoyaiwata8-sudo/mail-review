
import csv
import os
from typing import List, Dict, Optional
from datetime import datetime

# Columns for CHECK_LOG (Phase 5)
CSV_COLUMNS = [
    "case_id",
    "agent",
    "interaction_date",
    "channel",
    "audio_url",
    "transcript_url",
    "mail_url",
    "category",
    "check_item",
    "rating_symbol",
    "rating_num",
    "comment_good",
    "comment_improve",
    "evidence_quote",
    "evidence_timecode",
    "risk_flag",
    "next_step_draft",
    "hold_total_sec",
]

# Symbol to Score Mapping
SYMBOL_TO_SCORE = {"×": 1, "△": 2, "〇": 3, "◎": 4, "○": 3}

def _extract_date_str(case_id: str) -> str:
    """Extract YYYYMMDD from case_id and format as YYYY-MM-DD."""
    parts = case_id.rsplit("_", 1)
    if len(parts) == 2 and len(parts[1]) == 8:
        try:
            d = datetime.strptime(parts[1], "%Y%m%d")
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""

def result_to_check_rows(result: Dict) -> List[Dict]:
    """
    Expands an evaluation result into multiple rows for the check sheet.
    """
    rows = []
    case_id = result.get("case_id", "")
    agent = result.get("agent", "")
    channel = result.get("channel", "EMAIL")
    eval_data = result.get("evaluation", {})
    date_str = _extract_date_str(case_id)
    hold_total_sec = result.get("hold_total_sec", 0)
    
    # URLs
    audio_url = f"https://s3.travelstandard.jp/audio/{case_id}.mp3" if channel == "CALL" else ""
    mail_url = f"https://crm.travelstandard.jp/mail/{case_id}" if channel == "EMAIL" else ""

    scorecard = eval_data.get("scorecard", {})
    overall_comment = eval_data.get("overall_comment", "")
    good_points = eval_data.get("good_points", [])
    improvements = eval_data.get("improvements", [])
    draft = eval_data.get("next_step_draft", "")

    # 1. Expand Scorecard items
    for category_name, items in scorecard.items():
        if not isinstance(items, dict):
            continue
        for item_name, data in items.items():
            rank = data.get("rank", "△")
            comment = data.get("comment", "")
            
            rows.append({
                "case_id": case_id,
                "agent": agent,
                "interaction_date": date_str,
                "channel": channel,
                "audio_url": audio_url,
                "transcript_url": "",
                "mail_url": mail_url,
                "category": category_name,
                "check_item": item_name,
                "rating_symbol": rank,
                "rating_num": str(SYMBOL_TO_SCORE.get(rank, 0)),
                "comment_good": comment,
                "comment_improve": "",
                "evidence_quote": "",
                "evidence_timecode": "",
                "risk_flag": "",
                "next_step_draft": "",
                "hold_total_sec": hold_total_sec,
            })

    # 2. Add Good Points
    for i, gp in enumerate(good_points[:5]):
        rows.append({
            "case_id": case_id,
            "agent": agent,
            "interaction_date": date_str,
            "channel": channel,
            "category": "長所",
            "check_item": f"Good Point {i+1}",
            "comment_good": gp,
            "hold_total_sec": hold_total_sec,
        })

    # 3. Add Improvements
    for i, imp in enumerate(improvements[:5]):
        rows.append({
            "case_id": case_id,
            "agent": agent,
            "interaction_date": date_str,
            "channel": channel,
            "category": "課題",
            "check_item": f"Improvement {i+1}",
            "comment_improve": imp,
            "hold_total_sec": hold_total_sec,
        })

    # 4. Add Overall
    rows.append({
        "case_id": case_id,
        "agent": agent,
        "interaction_date": date_str,
        "channel": channel,
        "category": "総評",
        "check_item": "総合コメント",
        "comment_good": overall_comment,
        "next_step_draft": draft,
        "hold_total_sec": hold_total_sec,
    })

    return rows

def result_to_summary_row(result: Dict) -> Dict:
    """
    Creates a single summary row for an agent's evaluation.
    """
    case_id = result.get("case_id", "")
    agent = result.get("agent", "")
    channel = result.get("channel", "EMAIL")
    eval_data = result.get("evaluation", {})
    
    return {
        "Agent": agent,
        "Channel": channel,
        "Case ID": case_id,
        "Overall Summary": eval_data.get("overall_comment", ""),
        "Good Points": "; ".join(eval_data.get("good_points", [])[:3]),
        "Improvements": "; ".join(eval_data.get("improvements", [])[:3]),
        "Suggested Action": eval_data.get("next_step_draft", "")[:200] + "..." if eval_data.get("next_step_draft") else ""
    }

def export_phase5(results: List[Dict], call_path: str = "CHECK_LOG_CALL.csv", email_path: str = "CHECK_LOG_EMAIL.csv"):
    """
    Phase 5: Export results split by channel.
    """
    call_rows = []
    email_rows = []

    for res in results:
        rows = result_to_check_rows(res)
        if res.get("channel") == "CALL":
            call_rows.extend(rows)
        else:
            email_rows.extend(rows)

    # Save Call Logs
    if call_rows:
        with open(call_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(call_rows)
        print(f"Call logs saved to {call_path} ({len(call_rows)} rows)")

    # Save Email Logs
    if email_rows:
        with open(email_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(email_rows)
        print(f"Email logs saved to {email_path} ({len(email_rows)} rows)")

    return call_path, email_path

def export_to_excel_phase5(results: List[Dict], output_path: str = "weekly_check_sheet.xlsx"):
    """
    Phase 5: Generate Excel with two sheets.
    """
    if not results:
        print("No results to export to Excel.")
        return None

    try:
        import pandas as pd
        
        call_rows = []
        email_rows = []
        for res in results:
            rows = result_to_check_rows(res)
            if res.get("channel") == "CALL":
                call_rows.extend(rows)
            else:
                email_rows.extend(rows)

        if not call_rows and not email_rows:
            print("No evaluable rows to export to Excel.")
            return None

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 1. Summary Sheet
            summary_rows = [result_to_summary_row(r) for r in results if r.get("status") == "evaluated"]
            if summary_rows:
                pd.DataFrame(summary_rows).to_excel(writer, sheet_name="SUMMARY_REPORT", index=False)

            # 2. Detailed Logs
            if call_rows:
                pd.DataFrame(call_rows).to_excel(writer, sheet_name="CALL_LOG", index=False)
            if email_rows:
                pd.DataFrame(email_rows).to_excel(writer, sheet_name="EMAIL_LOG", index=False)
        
        print(f"Excel summary saved to {output_path}")
        return output_path
    except ImportError:
        print("pandas not installed. Skipping Excel generation.")
        return None
