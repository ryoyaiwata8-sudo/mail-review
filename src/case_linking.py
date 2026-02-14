
from typing import List, Dict
from collections import defaultdict
from datetime import timedelta
from src.data_ingestion import Interaction

class Case:
    def __init__(self, case_id: str):
        self.case_id = case_id
        self.interactions: List[Interaction] = []
        self.agent: str = "Unknown"

    def add_interaction(self, interaction: Interaction):
        self.interactions.append(interaction)
        # Update agent if unknown (assuming mostly same agent per case for this report scope)
        if self.agent == "Unknown" and interaction.agent != "Unknown":
            self.agent = interaction.agent

    @property
    def latest_timestamp(self):
        if not self.interactions:
            return None
        return max(i.timestamp for i in self.interactions)

    def __repr__(self):
        return f"<Case {self.case_id} | Agent: {self.agent} | Interactions: {len(self.interactions)}>"

class CaseLinker:
    def link_cases(self, interactions: List[Interaction]) -> List[Case]:
        cases = []
        
        # Strategy: Group by Agent -> then Time clustering (Simple logic: Same Day)
        # Why? Because we can't link Phone to Email via ID effectively yet.
        # But report is "Weekly", so maybe "By Agent" is the primary grouping for the REPORT,
        # but for the "Case" (topic), we want to group related interactions.
        
        # 1. Group by Agent
        interactions_by_agent = defaultdict(list)
        for i in interactions:
            interactions_by_agent[i.agent].append(i)
            
        for agent, agent_interactions in interactions_by_agent.items():
            # Sort by timestamp
            agent_interactions.sort(key=lambda x: x.timestamp)
            
            # Simple clustering: If interactions are within X hours/days, group them?
            # Or just "Daily Case"?
            # Let's try grouping by Date for now.
            daily_groups = defaultdict(list)
            for i in agent_interactions:
                date_key = i.timestamp.date()
                daily_groups[date_key].append(i)
                
            for date, day_interactions in daily_groups.items():
                # Create a case for this day for this agent
                # This is a simplification. A real case might span days. 
                # But for "Sample Selection per Agent", picking a "Day's work" or "One Interaction" is a start.
                
                # Further refinement: If there is a Phone call, maybe that defines the case?
                # Let's create a Case for EACH Phone call, and try to attach nearby Emails?
                # Or just treat everything on that day as one "Case" (Work Day context)?
                
                # Let's go with: 1 Case = 1 Cluster of interactions on same day (for now).
                case_id = f"CASE_{agent}_{date.strftime('%Y%m%d')}"
                case = Case(case_id)
                for interaction in day_interactions:
                    case.add_interaction(interaction)
                cases.append(case)
                
        return cases
