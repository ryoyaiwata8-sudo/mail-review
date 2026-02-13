
from typing import List, Dict
import random
import json
from src.case_linking import Case

class LLMClient:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

class MockLLMClient(LLMClient):
    def generate(self, prompt: str) -> str:
        # Return a mock JSON string mimicking the grading output
        return json.dumps({
            "scores": {
                "politeness": random.randint(3, 5),
                "clarity": random.randint(3, 5),
                "accuracy": random.randint(3, 5),
                "empathy": random.randint(3, 5)
            },
            "comment": "全体的に丁寧な対応です。専門用語の解説も分かりやすく、顧客の不安を解消できています。",
            "evidence": "「ご不安なお気持ち、お察しいたします」という発言が寄り添いを感じさせます。",
            "improvement": "保留時間が少し長かったため、途中経過の報告があるとより良いです。"
        }, ensure_ascii=False)

class Evaluator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def evaluate_case(self, case: Case) -> Dict:
        # Construct prompt based on case content
        conversation_text = ""
        for i in case.interactions:
            conversation_text += f"[{i.type}] {i.timestamp}\nSubject: {i.subject}\nBody/Transcript: {i.body}\n---\n"
            
        prompt = f"""
        You are a QA Specialist. Evaluate the following customer support interaction.
        Interaction:
        {conversation_text}
        
        Output JSON with scores (1-5), comment, evidence, and improvement.
        """
        
        response = self.llm.generate(prompt)
        try:
            result = json.loads(response)
        except:
            result = {"error": "Failed to parse LLM response"}
            
        return {
            "case_id": case.case_id,
            "agent": case.agent,
            "evaluation": result
        }

    def evaluate_batch(self, cases: List[Case]) -> List[Dict]:
        results = []
        for case in cases:
            results.append(self.evaluate_case(case))
        return results
