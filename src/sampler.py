
from typing import List, Dict
import random
from src.case_linking import Case

class Sampler:
    def __init__(self, phone_count: int = 1, email_count: int = 3):
        self.phone_count = phone_count
        self.email_count = email_count

    def select_samples(self, cases: List[Case]) -> List[Case]:
        selected_cases = []
        cases_by_agent = {}
        
        for case in cases:
            if case.agent not in cases_by_agent:
                cases_by_agent[case.agent] = {'PHONE': [], 'EMAIL': []}
            
            # Determine primary type of case for selection
            has_phone = any(i.type == 'PHONE' for i in case.interactions)
            if has_phone:
                cases_by_agent[case.agent]['PHONE'].append(case)
            else:
                cases_by_agent[case.agent]['EMAIL'].append(case)
                
        for agent, pools in cases_by_agent.items():
            # Select Phone Cases
            phones = pools['PHONE']
            selected_phones = random.sample(phones, min(len(phones), self.phone_count))
            selected_cases.extend(selected_phones)
            
            # Select Email Cases
            emails = pools['EMAIL']
            selected_emails = random.sample(emails, min(len(emails), self.email_count))
            selected_cases.extend(selected_emails)
            
        return selected_cases
