
from typing import List, Dict, Tuple, Optional
from datetime import date, datetime, timedelta
import random
import re
from src.case_linking import Case


class Sampler:
    def __init__(self, target_per_agent: int = 1):
        self.target_per_agent = target_per_agent
        # Phase 5 Thresholds (Strict)
        self.STRICT_GATES = {
            "EMAIL": {"min_chars": 350, "structure_points": 2},
            "CALL": {"min_transcript": 600, "structure_points": 1, "min_duration": 120}
        }
        # Phase 6 Thresholds (Loose Fallback)
        self.LOOSE_GATES = {
            "EMAIL": {"min_chars": 150, "structure_points": 1},
            "CALL": {"min_transcript": 300, "structure_points": 0, "min_duration": 60}
        }

    def split_by_period(
        self, cases: List[Case], start_date: date, end_date: date
    ) -> Tuple[List[Case], List[Case]]:
        """Split cases into in_range and out_of_range based on target period."""
        in_range = []
        out_of_range = []

        for case in cases:
            case_date = self._extract_date(case)
            if case_date and start_date <= case_date <= end_date:
                in_range.append(case)
            else:
                out_of_range.append(case)

        return in_range, out_of_range

    def _extract_date(self, case: Case) -> Optional[date]:
        """Extract date from case_id or interactions."""
        parts = case.case_id.rsplit("_", 1)
        if len(parts) == 2:
            try:
                return datetime.strptime(parts[1], "%Y%m%d").date()
            except ValueError:
                pass
        if case.interactions:
            return max(i.timestamp for i in case.interactions).date()
        return None

    def is_eligible(self, case: Case, mode: str = "strict") -> Tuple[bool, str, str]:
        """
        Gating logic (Phase 6).
        mode: 'strict' or 'loose'
        Returns: (is_eligible, channel, reason)
        """
        gates = self.STRICT_GATES if mode == "strict" else self.LOOSE_GATES
        has_phone = any(i.type == "PHONE" for i in case.interactions)
        
        if has_phone:
            content = "".join([i.body or "" for i in case.interactions if i.type == "PHONE"])
            # Call Gate
            if len(content) >= gates["CALL"]["min_transcript"]:
                return True, "CALL", f"Transcript({len(content)}) >= {gates['CALL']['min_transcript']} ({mode})"
            
            # Structure rescue
            rescue_points = 0
            if re.search(r"(確認|承知|左記)", content): rescue_points += 1
            if re.search(r"(\d+円|日程|期限|手配)", content): rescue_points += 1
            
            if len(content) > 100 and rescue_points >= gates["CALL"]["structure_points"]:
                return True, "CALL", f"Structure rescue ({mode}, points={rescue_points})"
            
            return False, "CALL", f"Call too short ({len(content)})"
        
        else:
            # Email Gate
            content = "".join([i.body or "" for i in case.interactions if i.type == "EMAIL"])
            if len(content) >= gates["EMAIL"]["min_chars"]:
                return True, "EMAIL", f"Email({len(content)}) >= {gates['EMAIL']['min_chars']} ({mode})"
            
            # Structure rescue
            rescue_points = 0
            if re.search(r"(\d\.|・|■)", content): rescue_points += 1 
            if re.search(r"(\d+円|月\s*\d+日|泊|期限)", content): rescue_points += 1 
            if re.search(r"(お願い|送付|回答)", content): rescue_points += 1 
            
            if len(content) > 50 and rescue_points >= gates["EMAIL"]["structure_points"]:
                return True, "EMAIL", f"Structure rescue ({mode}, points={rescue_points})"
            
            return False, "EMAIL", f"Email too short ({len(content)})"

    def select_samples_phase6(self, cases: List[Case], all_cases: List[Case], start_date: date, end_date: date) -> List[Dict]:
        """
        Phase 6: EMAILx1 + CALLx1 strict per Agent with Fallback Hierarchy.
        1. Try Strict Gate (Current Week).
        2. Try Loose Gate (Current Week).
        3. Try Strict Gate (Extended Week: +/- 7 days).
        4. Final: No data.
        """
        agents = sorted(list(set(c.agent for c in all_cases if c.agent != "Unknown")))
        results = []

        for agent in agents:
            # --- 1. CALL Selection ---
            call_selection = self._select_best(agent, "PHONE", cases, all_cases, start_date, end_date)
            # --- 2. EMAIL Selection ---
            email_selection = self._select_best(agent, "EMAIL", cases, all_cases, start_date, end_date)
            
            results.append({
                "agent": agent,
                "call_case": call_selection,
                "email_case": email_selection
            })

        return results

    def _select_best(self, agent: str, channel_type: str, cur_cases: List[Case], all_cases: List[Case], start_date: date, end_date: date) -> Dict:
        """Helper to find one case using hierarchy."""
        
        # Filter pools
        agent_cur = [c for c in cur_cases if c.agent == agent]
        # Identify by content type (Heuristic)
        if channel_type == "PHONE":
            agent_cur_pool = [c for c in agent_cur if any(i.type == "PHONE" for i in c.interactions)]
        else:
            agent_cur_pool = [c for c in agent_cur if not any(i.type == "PHONE" for i in c.interactions)]

        # --- Tier 1: Strict Gate (Current Week) ---
        candidates = [c for c in agent_cur_pool if self.is_eligible(c, mode="strict")[0]]
        if candidates:
            c = random.choice(candidates)
            return {"case": c, "status": "selected", "reason": self.is_eligible(c, mode="strict")[2], "fallback": None}

        # --- Tier 2: Loose Gate (Current Week) ---
        candidates = [c for c in agent_cur_pool if self.is_eligible(c, mode="loose")[0]]
        if candidates:
            c = random.choice(candidates)
            return {"case": c, "status": "selected", "reason": self.is_eligible(c, mode="loose")[2], "fallback": "loose_gate"}

        # --- Tier 3: Strict Gate (Extended Range +/- 7 days) ---
        extended_start = start_date - timedelta(days=7)
        extended_end = end_date + timedelta(days=7)
        ext_cases = [c for c in all_cases if c.agent == agent]
        if channel_type == "PHONE":
            ext_pool = [c for c in ext_cases if any(i.type == "PHONE" for i in c.interactions)]
        else:
            ext_pool = [c for c in ext_cases if not any(i.type == "PHONE" for i in c.interactions)]
        
        # Only check cases NOT in current range
        ext_pool = [c for c in ext_pool if not (start_date <= self._extract_date(c) <= end_date)]
        # Filter by extended date
        ext_pool = [c for c in ext_pool if extended_start <= self._extract_date(c) <= extended_end]
        
        candidates = [c for c in ext_pool if self.is_eligible(c, mode="strict")[0]]
        if candidates:
            c = random.choice(candidates)
            return {"case": c, "status": "selected", "reason": self.is_eligible(c, mode="strict")[2], "fallback": "date_widening"}

        # --- Tier 4: No data ---
        return {"case": None, "status": "skipped", "reason": "No evaluable candidates in target or extended range.", "fallback": None}
