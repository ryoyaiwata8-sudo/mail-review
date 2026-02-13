
import os
from src.data_ingestion import DataIngestion
from src.case_linking import CaseLinker
from src.sampler import Sampler
from src.evaluator import Evaluator, MockLLMClient
from src.reporter import Reporter

def main():
    data_dir = r"c:\Users\ryoya\.gemini\antigravity\playground\thermal-coronal\data"
    
    print("--- Starting Weekly Report System ---")
    
    # Step 0: Data Ingestion
    print("Loading data...")
    ingestion = DataIngestion(data_dir)
    interactions = ingestion.load_all()
    print(f"Loaded {len(interactions)} interactions.")
    
    # Step 1: Case Linking
    print("Linking cases...")
    linker = CaseLinker()
    cases = linker.link_cases(interactions)
    print(f"Generated {len(cases)} cases.")
    
    # Step 2: Sample Selection
    print("Selecting samples...")
    sampler = Sampler(phone_count=1, email_count=2)
    selected_cases = sampler.select_samples(cases)
    print(f"Selected {len(selected_cases)} cases for evaluation.")
    
    # Step 3: Evaluation
    print("Evaluating cases...")
    llm = MockLLMClient()
    evaluator = Evaluator(llm)
    results = evaluator.evaluate_batch(selected_cases)
    
    # Step 4: Report Generation
    print("Generating report...")
    reporter = Reporter()
    report_content = reporter.generate_report(results)
    
    output_path = "weekly_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Report saved to {output_path}")

if __name__ == "__main__":
    main()
