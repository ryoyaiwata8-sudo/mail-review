
from typing import List, Dict
from datetime import datetime

class Reporter:
    def generate_report(self, results: List[Dict]) -> str:
        report = f"# Add-On Value Weekly Report - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        # Group by Agent
        results_by_agent = {}
        for res in results:
            agent = res['agent']
            if agent not in results_by_agent:
                results_by_agent[agent] = []
            results_by_agent[agent].append(res)
            
        for agent, agent_results in results_by_agent.items():
            report += f"## Agent: {agent}\n\n"
            
            # Summary Section (Mock aggregation)
            total_cases = len(agent_results)
            avg_politeness = sum(r['evaluation']['scores']['politeness'] for r in agent_results) / total_cases
            report += f"**Cases Reviewed**: {total_cases}\n"
            report += f"**Avg Politeness**: {avg_politeness:.1f}/5.0\n\n"
            
            for res in agent_results:
                eval_data = res['evaluation']
                case_id = res['case_id']
                
                report += f"### Case: {case_id}\n"
                report += f"- **Scores**: {eval_data['scores']}\n"
                report += f"- **Comment**: {eval_data['comment']}\n"
                report += f"- **Good Point (Evidence)**: {eval_data.get('evidence', 'N/A')}\n"
                report += f"- **Improvement**: {eval_data.get('improvement', 'N/A')}\n\n"
                
            report += "---\n\n"
            
        return report
