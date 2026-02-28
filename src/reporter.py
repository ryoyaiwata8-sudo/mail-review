
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
        
        eval_count = len([r for r in final_results if r.get("status") == "evaluated"])
        report += f"> **ステータス**: 評価済み: {eval_count}件 | 対象期間内全データ: {len(final_results)}件\n\n"
        
        # Group by Agent
        results_by_agent = {}
        for res in final_results:
            agent = res["agent"]
            if agent not in results_by_agent:
                results_by_agent[agent] = {"CALL": None, "EMAIL": None}
            
            # Use evaluated if available, else keep the skipped record
            if res.get("status") == "evaluated" or results_by_agent[agent][res.get("channel")] is None:
                results_by_agent[agent][res.get("channel")] = res

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
        tour_code = eval_data.get("tour_code", "N/A")
        hold_time = res.get("hold_total_sec", 0)
        total_time = res.get("total_duration_sec", 0)
        hold_ratio = (hold_time / total_time * 100) if total_time > 0 else 0
        
        fallback = res.get("fallback", "strict")
        
        section = f"**ケースID**: {case_id} ({fallback})\n"
        section += f"**ツアーコード**: {tour_code}\n"
        
        if res.get("channel") == "CALL":
            section += f"**保留時間**: 合計 {hold_time:.1f}秒 (通話時間の {hold_ratio:.1f}%)\n"
        
        section += "\n"
        
        # Scorecard
        scorecard = eval_data.get("scorecard", {})
        if scorecard:
            section += "| カテゴリ | 項目 | 評価 | 根拠(evidence) | フィードバック |\n"
            section += "|---|---|:---:|---|---|\n"
            for cat, items in scorecard.items():
                for item, data in items.items():
                    rank = data.get("rank", "N/A")
                    evidence = data.get("evidence", "-")
                    comment = data.get("comment", "-")
                    section += f"| {cat} | {item} | {rank} | {evidence} | {comment} |\n"
            section += "\n"

        section += f"**■ 総評**\n{eval_data.get('overall_comment', 'N/A')}\n\n"

        # Points
        good_points = eval_data.get("良かった点", [])
        if good_points:
            section += "**📌 良かった点**\n"
            for p in good_points:
                section += f"- {p}\n"
            section += "\n"

        improvements = eval_data.get("改善点", [])
        if improvements:
            section += "**💡 改善点**\n"
            for p in improvements:
                section += f"- {p}\n"
            section += "\n"

        # AI Metrics
        metrics = eval_data.get("ai_metrics", {})
        if metrics:
            spin = "あり" if metrics.get("spin_applied") else "なし"
            risk = metrics.get("risk_level", "Unknown")
            section += f"> **AI指標**: SPIN適用: {spin} | リスクレベル: {risk}\n\n"

        return section
