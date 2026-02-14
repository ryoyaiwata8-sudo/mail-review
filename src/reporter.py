
import os
from typing import List, Dict, Optional
from datetime import datetime, date

SCORE_SYMBOLS = {4: "◎", 3: "〇", 2: "△", 1: "×"}

def score_to_symbol(val: int) -> str:
    return SCORE_SYMBOLS.get(val, "N/A")

class Reporter:
    def __init__(self, mode: str = "score"):
        """
        mode: 'score' (default) or 'coach'
        """
        self.mode = os.getenv("OUTPUT_MODE", mode).lower()

    def generate_report(
        self,
        final_results: List[Dict],
        start_date: date,
        end_date: date,
    ) -> str:
        report = f"# 週次評価レポート ({self.mode.upper()} MODE) - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        report += f"## 対象期間: {start_date} ～ {end_date}\n\n"

        # Group by Agent
        results_by_agent = {}
        for res in final_results:
            agent = res["agent"]
            if agent not in results_by_agent:
                results_by_agent[agent] = {"CALL": None, "EMAIL": None}
            
            if res.get("status") == "evaluated":
                channel = res.get("channel")
                results_by_agent[agent][channel] = res
            elif res.get("status") == "skipped":
                # Keep track of skipped for reason display
                channel = res.get("channel")
                results_by_agent[agent][channel] = res

        for agent, bundles in sorted(results_by_agent.items()):
            report += f"## エージェント: {agent}\n\n"

            # 1. CALL Section
            report += "### 【電話応対】\n"
            call_res = bundles["CALL"]
            if call_res and call_res.get("status") == "evaluated":
                report += self._format_case_section(call_res)
            else:
                reason = call_res.get("reason", "不明") if call_res else "データなし"
                report += f"> **評価対象なし**: {reason}\n\n"

            # 2. EMAIL Section
            report += "### 【メール応対】\n"
            email_res = bundles["EMAIL"]
            if email_res and email_res.get("status") == "evaluated":
                report += self._format_case_section(email_res)
            else:
                reason = email_res.get("reason", "不明") if email_res else "データなし"
                report += f"> **評価対象なし**: {reason}\n\n"

            report += "---\n\n"

        return report

    def _format_case_section(self, res: Dict) -> str:
        eval_data = res.get("evaluation", {})
        case_id = res.get("case_id", "Unknown Case")
        hold_time = res.get("hold_total_sec", 0)
        hold_segments = res.get("hold_segments", [])
        fallback = res.get("fallback", "strict")
        
        section = f"**ケースID**: {case_id} ({fallback})\n"
        
        if res.get("channel") == "CALL":
            section += f"**保留時間**: 合計 {hold_time}秒"
            if hold_segments:
                seg_detail = ", ".join([f"{s['start']}s-{s['end']}s({s['duration']}s)" for s in hold_segments])
                section += f" [内訳: {seg_detail}]"
            section += "\n"
        
        section += "\n"
        
        # Scorecard (Only in Score Mode)
        if self.mode == "score":
            scorecard = eval_data.get("scorecard", {})
            if scorecard:
                section += "| カテゴリ | 項目 | 評価 | 1行フィードバック |\n"
                section += "|---|---|:---:|---|\n"
                for cat, items in scorecard.items():
                    for item, data in items.items():
                        section += f"| {cat} | {item} | {data.get('rank')} | {data.get('comment')} |\n"
                section += "\n"

        section += f"**■ 総評**\n{eval_data.get('overall_comment', 'N/A')}\n\n"

        gp = eval_data.get("good_points", [])
        if gp:
            section += "**👍 Good Points**\n"
            for p in gp[:5]:
                section += f"- {p}\n"
            section += "\n"

        imp = eval_data.get("improvements", [])
        if imp:
            section += "**💡 Improvements**\n"
            for p in imp[:5]:
                section += f"- {p}\n"
            section += "\n"

        draft = eval_data.get("next_step_draft")
        if draft:
            section += f"**📩 推奨アクション（返信案）**\n```text\n{draft}\n```\n\n"

        return section
