
from typing import List, Dict, Optional
import os
import random
import json
import google.generativeai as genai
from openai import OpenAI
from src.case_linking import Case

# === Phase 5: Channel-specific Masters ===
MASTER_ITEMS_CALL = {
    "基本応対": ["敬語", "礼儀", "声", "滑舌", "クッション言葉", "問合い対応"],
    "ヒアリング姿勢": ["ヒアリング", "傾聴", "状況質問"],
    "SPIN話法": ["問題質問", "示唆質問", "解決質問"]
}

MASTER_ITEMS_EMAIL = {
    "基本応対": ["敬語", "礼儀", "文章構成", "視覚的工夫", "クッション言葉", "問合い対応"],
    "ヒアリング姿勢": ["ヒアリング", "傾聴", "状況質問"],
    "SPIN話法": ["問題質問", "示唆質問", "解決質問"]
}

# === Symbol Mapping (Phase 5) ===
# 1=×, 2=△, 3=〇, 4=◎
SYMBOL_TO_SCORE = {"×": 1, "△": 2, "〇": 3, "◎": 4, "○": 3} # ○ is allowed as alias for 〇
SCORE_TO_SYMBOL = {1: "×", 2: "△", 3: "〇", 4: "◎"}

class LLMClient:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

class GeminiLLMClient(LLMClient):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return json.dumps({"error": str(e)})

class Evaluator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def evaluate_case(self, case: Case) -> Dict:
        """Evaluate a single case (Phase 5: Channel-specific)."""
        
        # Identify channel (prefer CALL if present)
        channel = "EMAIL"
        if any(i.type == "PHONE" for i in case.interactions):
            channel = "CALL"
        
        master = MASTER_ITEMS_CALL if channel == "CALL" else MASTER_ITEMS_EMAIL
        
        # Build conversation text
        conversation_text = ""
        for i in case.interactions:
            content = i.body if i.body else "(No content)"
            conversation_text += (
                f"\n[{i.type}] {i.timestamp}\n"
                f"Subject: {i.subject}\n"
                f"Content: {content}\n---\n"
            )

        # Build schema string for JSON instructions
        schema_parts = []
        for cat, items in master.items():
            item_schema = ", ".join([f'"{item}": {{ "rank": "×|△|〇|◎", "comment": "str" }}' for item in items])
            schema_parts.append(f'"{cat}": {{ {item_schema} }}')
        scorecard_schema = ", ".join(schema_parts)

        prompt = f"""あなたは「トラベルスタンダードジャパン」の品質管理責任者として、エージェントの{channel}応対を評価してください。

**評価対象コンテキスト:**
{conversation_text}

**評価ルール:**
1. **チャネル特性の考慮**: {channel}特有のポイント（電話なら声のトーン、メールなら視覚的構成など）を重点的に。
2. **スコア記号の厳守**: 以下の4段階のみを使用してください。
   - ◎ (4点): 完璧。他者の模範となる。
   - 〇 (3点): 基本ができている。問題なし。
   - △ (2点): やや課題あり。改善の余地。
   - × (1点): 重大な課題。至急の教育が必要。
3. **1行コメント**: 各項目20〜40文字程度の具体的なフィードバック。
4. **構造化出力**: 箇条書きと簡潔な総評。

**出力JSONフォーマット:**
{{
    "scorecard": {{
        {scorecard_schema}
    }},
    "overall_comment": "最大3行の総評",
    "good_points": ["点目1", "点目2", "..."],
    "improvements": ["改善1", "改善2", "..."],
    "next_step_draft": "返信ドラフト全文",
    "ai_metrics": {{
        "spin_tags": {{ "situation": int, "problem": int, "implication": int, "need_payoff": int }},
        "risk_flags": ["リスク内容"]
    }}
}}

**重要:** JSON以外のテキストは決して含めないでください。
"""

        response_text = self.llm.generate(prompt)
        cleaned = response_text.replace("```json", "").replace("```", "").strip()

        try:
            result = json.loads(cleaned)
        except Exception as e:
            print(f"[ERROR] JSON parse failed: {e}")
            result = {"error": str(e), "raw": response_text[:200]}

        return {
            "case_id": case.case_id,
            "agent": case.agent,
            "channel": channel,
            "status": "evaluated",
            "evaluation": result,
        }

    def evaluate_batch(self, cases: List[Case]) -> List[Dict]:
        return [self.evaluate_case(c) for c in cases]
