
from typing import List, Dict, Optional
import os
import random
import json
import google.generativeai as genai
from openai import OpenAI
from src.case_linking import Case

# === Symbol Mapping ===
SYMBOL_TO_SCORE = {"×": 1, "△": 2, "〇": 3, "◎": 4, "○": 3}
SCORE_TO_SYMBOL = {1: "×", 2: "△", 3: "〇", 4: "◎"}

class LLMClient:
    def generate(self, prompt: str, files: Optional[List] = None) -> str:
        raise NotImplementedError

class GeminiLLMClient(LLMClient):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-flash-latest")
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str, files: Optional[List] = None) -> str:
        try:
            inputs = []
            if files:
                inputs.extend(files)
            inputs.append(prompt)
            response = self.model.generate_content(inputs)
            if not response.parts:
                print(f"[DEBUG] Empty response parts. Prompt feedback: {response.prompt_feedback}")
                return json.dumps({"error": "Empty response", "feedback": str(response.prompt_feedback)})
            return response.text
        except Exception as e:
            print(f"[ERROR] Gemini generation failed: {e}")
            return json.dumps({"error": str(e)})

class Evaluator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def evaluate_case(self, case: Case) -> Dict:
        has_phone = any(i.type == "PHONE" for i in case.interactions)
        channel = "CALL" if has_phone else "EMAIL"
        target_type = "PHONE" if channel == "CALL" else "EMAIL"
        filtered_interactions = [i for i in case.interactions if i.type == target_type]
        
        if not filtered_interactions:
            return {
                "case_id": case.case_id,
                "agent": case.agent,
                "channel": channel,
                "status": "skipped",
                "reason": f"No {target_type} interactions found."
            }

        conversation_text = ""
        audio_files = []
        for i in filtered_interactions:
            content = i.body if i.body else "(No content)"
            conversation_text += f"\n[{i.type}] {i.timestamp}\nSubject: {i.subject}\nContent: {content}\n---\n"
            if i.type == "PHONE" and i.file_path and os.path.exists(i.file_path):
                try:
                    audio_file = genai.upload_file(path=i.file_path)
                    import time
                    while audio_file.state.name == "PROCESSING":
                        time.sleep(1)
                        audio_file = genai.get_file(audio_file.name)
                    audio_files.append(audio_file)
                except Exception as e:
                    print(f"[WARNING] Audio upload failed: {e}")

        prompt = self._build_prompt(channel, conversation_text, has_audio=len(audio_files) > 0)
        
        result = {}
        for attempt in range(2):
            response_text = self.llm.generate(prompt, files=audio_files if audio_files else None)
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            try:
                result = json.loads(cleaned)
                if "scorecard" in result:
                    break
            except Exception as e:
                print(f"[DEBUG] JSON parse failed (Attempt {attempt+1}): {e}")
                if attempt == 0:
                    prompt += "\nOutput ONLY valid JSON."
                else:
                    result = {"error": "JSON parse failed", "raw": response_text[:500]}

        return {
            "case_id": case.case_id,
            "agent": case.agent,
            "channel": channel,
            "status": "evaluated",
            "evaluation": result,
        }

    def _build_prompt(self, channel: str, conversation_text: str, has_audio: bool) -> str:
        audio_instruction = ""
        items_json = ""
        
        if channel == "CALL":
            if has_audio:
                audio_instruction = "- **音声評価 (AUDIO)**: トーン（声の調子）、滑舌（明瞭性）、話速（テンポ）、沈黙（間）、遮り（被せ）を直接の「音」から評価してください。"
            else:
                audio_instruction = "- **音声評価 (AUDIO)**: 音声なし。声、滑舌、話速、沈黙、遮りの項目はすべて rank: NA、evidence: 音声なし としてください。"
            
            items_json = """
        "基本応対": {
            "敬語": { "rank": "◎|〇|△|×|NA", "comment": "30字", "evidence": "[00:10] 「～」" },
            "礼儀": { "rank": "...", "comment": "...", "evidence": "..." },
            "声": { "rank": "...", "comment": "...", "evidence": "..." },
            "滑舌": { "rank": "...", "comment": "...", "evidence": "..." },
            "クッション言葉": { "rank": "...", "comment": "...", "evidence": "..." },
            "問合い対応": { "rank": "...", "comment": "...", "evidence": "..." }
        },
        "ヒアリング・傾聴": {
            "ヒアリング": { "rank": "...", "comment": "...", "evidence": "..." },
            "傾聴": { "rank": "...", "comment": "...", "evidence": "..." }
        },
        "SPIN話法": {
            "状況質問": { "rank": "...", "comment": "...", "evidence": "..." },
            "問題質問": { "rank": "...", "comment": "...", "evidence": "..." },
            "示唆質問": { "rank": "...", "comment": "...", "evidence": "..." },
            "解決質問": { "rank": "...", "comment": "...", "evidence": "..." }
        }"""
        else:
            # EMAIL items based on user's image request
            items_json = """
        "基本応対": {
            "敬語": { "rank": "◎|〇|△|×|NA", "comment": "30字", "evidence": "本文引用" },
            "礼儀": { "rank": "...", "comment": "...", "evidence": "..." },
            "文章構成": { "rank": "...", "comment": "...", "evidence": "..." },
            "視覚的工夫": { "rank": "...", "comment": "...", "evidence": "..." },
            "クッション言葉": { "rank": "...", "comment": "...", "evidence": "..." },
            "問合い対応": { "rank": "...", "comment": "...", "evidence": "..." }
        },
        "ヒアリング": {
            "ヒアリング": { "rank": "...", "comment": "...", "evidence": "..." },
            "傾聴": { "rank": "...", "comment": "...", "evidence": "..." },
            "状況質問": { "rank": "...", "comment": "...", "evidence": "..." }
        },
        "SPIN話法": {
            "問題質問": { "rank": "...", "comment": "...", "evidence": "..." },
            "示唆質問": { "rank": "...", "comment": "...", "evidence": "..." },
            "解決質問": { "rank": "...", "comment": "...", "evidence": "..." }
        }"""

        return f"""あなたは「トラベルスタンダードジャパン」の品質責任者として、{channel}応対を厳格に評価してください。

**評価対象ログ:**
{conversation_text}

**最重要ルール:**
1. **予約番号 (booking_id)**: ログ内に「予約番号」「RESERVATION」等（例：12345）があれば抽出してください。なければ空文字。
2. **ツアーコード (tour_code)**: ログ内に「TI-12345」のようなツアーコードがあれば抽出してください。
3. **日時特定**: 評価対象となった応対の正確な日時（年-月-日 時:分:秒）を特定してください。
4. **根拠引用 (evidence)**: 全項目で具体的な発言を引用してください。電話の場合は [01:23] のようなタイムスタンプを必ず含めてください。
5. **良かった点 (3〜5件) / 改善点 (1〜3件)**: それぞれ具体的に抽出してください。無理に最大件数まで埋める必要はありませんが、最低件数は満たすようにしてください。

**出力形式 (JSONのみ、他のテキスト一切禁止):**
{{
    "booking_id": "12345",
    "tour_code": "TI-XXXXX",
    "interaction_datetime": "YYYY-MM-DD HH:MM:SS",
    "scorecard": {{{items_json}
    }},
    "良かった点": ["1...", "2...", "3...", "4...", "5..."],
    "改善点": ["1...", "2...", "3..."],
    "overall_comment": "...",
    "ai_metrics": {{ "spin_applied": bool, "risk_level": "Low|Medium|High" }}
}}
{audio_instruction}
"""

    def evaluate_batch(self, cases: List[Case]) -> List[Dict]:
        return [self.evaluate_case(c) for c in cases]
