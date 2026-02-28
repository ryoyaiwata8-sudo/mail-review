
import csv
import os
from typing import List, Dict, Optional
from datetime import datetime

# Columns for CHECK_LOG
CSV_COLUMNS = [
    "case_id",
    "booking_id",
    "agent",
    "interaction_date",
    "tour_code",
    "hold_ratio",
    "interaction_url",
    "category",
    "check_item",
    "rating_symbol",
    "rating_num",
    "comment",
    "evidence"
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
    Updated for Phase 9 (Full Timestamp, Separate Links).
    """
    rows = []
    case_id = result.get("case_id", "")
    agent = result.get("agent", "")
    channel = result.get("channel", "EMAIL")
    eval_data = result.get("evaluation", {})
    
    # Booking ID
    booking_id = eval_data.get("booking_id", "")
    
    # Use AI-extracted datetime if available, otherwise fallback to date from case_id
    interaction_dt = eval_data.get("interaction_datetime", "")
    if not interaction_dt or "Y" in interaction_dt:
        interaction_dt = _extract_date_str(case_id)
    
    # Format Tour Code to preserve leading zeros in Excel: ="02841"
    raw_tour_code = eval_data.get("tour_code", "")
    tour_code = f'="{raw_tour_code}"' if raw_tour_code and raw_tour_code.isdigit() else raw_tour_code
    
    # Hold Ratio calculation (Only for CALL)
    if channel == "CALL":
        hold_sec = result.get("hold_total_sec", 0)
        total_sec = result.get("total_duration_sec", 0)
        hold_ratio_str = f"{(hold_sec / total_sec * 100):.1f}%" if total_sec > 0 else "0.0%"
    else:
        hold_ratio_str = ""
    
    # Interaction URL
    if channel == "CALL":
        interaction_url = f"https://s3.travelstandard.jp/audio/{case_id}.mp3"
    else:
        interaction_url = f"https://s3.travelstandard.jp/email/view/{case_id}.html"

    scorecard = eval_data.get("scorecard", {})
    overall_comment = eval_data.get("overall_comment", "")
    good_points = eval_data.get("良かった点", [])
    improvements = eval_data.get("改善点", [])

    items_to_process = []
    
    # 1. Flatten Scorecard items
    for category_name, items in scorecard.items():
        if not isinstance(items, dict): continue
        for item_name, data in items.items():
            items_to_process.append({
                "category": category_name,
                "item": item_name,
                "rank": data.get("rank", "NA"),
                "comment": data.get("comment", ""),
                "evidence": data.get("evidence", "")
            })

    # 2. Add Good Points
    for i, p in enumerate(good_points):
        items_to_process.append({
            "category": "振り返り",
            "item": f"良かった点 {i+1}",
            "comment": p
        })

    # 3. Add Improvements
    for i, p in enumerate(improvements):
        items_to_process.append({
            "category": "振り返り",
            "item": f"改善点 {i+1}",
            "comment": p
        })
        
    # 4. Add Summary Row (Overall Comment)
    items_to_process.append({
        "category": "総評",
        "item": "全体コメント",
        "comment": overall_comment
    })

    # Convert to CSV rows with deduplication
    for i, item in enumerate(items_to_process):
        is_first = (i == 0)
        row = {
            "case_id": case_id if is_first else "",
            "booking_id": booking_id if is_first else "",
            "agent": agent if is_first else "",
            "interaction_date": interaction_dt if is_first else "",
            "tour_code": tour_code if is_first else "",
            "hold_ratio": hold_ratio_str if is_first else "",
            "interaction_url": interaction_url if is_first else "",
            "category": item.get("category", ""),
            "check_item": item.get("item", ""),
            "rating_symbol": item.get("rank", ""),
            "rating_num": str(SYMBOL_TO_SCORE.get(item.get("rank"), "")) if "rank" in item else "",
            "comment": item.get("comment", ""),
            "evidence": item.get("evidence", "")
        }
        rows.append(row)

    return rows

def export_phase5(results: List[Dict], call_path: str = "CHECK_LOG_CALL.csv", email_path: str = "CHECK_LOG_EMAIL.csv"):
    """Main export function for Phase 9."""
    call_rows = []
    email_rows = []

    for res in results:
        rows = result_to_check_rows(res)
        if res.get("channel") == "CALL":
            call_rows.extend(rows)
        else:
            email_rows.extend(rows)

    if call_rows:
        with open(call_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(call_rows)
        print(f"Call logs saved to {call_path} ({len(call_rows)} rows)")

    if email_rows:
        with open(email_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(email_rows)
        print(f"Email logs saved to {email_path} ({len(email_rows)} rows)")

    return call_path, email_path

def export_to_excel_phase5(results, path):
    pass
