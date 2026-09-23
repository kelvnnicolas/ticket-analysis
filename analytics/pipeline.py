import json
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extraction.postgres_client import PostgresExtractor
from transformation.cleaner import DataCleaner
from metrics.calculator import MetricsCalculator

def run_pipeline():
    print("🚀 Starting SupportOps Analytics Pipeline...")
    
    extractor = PostgresExtractor()
    print("1. Extracting data from PostgreSQL...")
    raw_tickets = extractor.extract_tickets_with_context()
    raw_history = extractor.extract_ticket_history()
    
    cleaner = DataCleaner()
    print("2. Cleaning and transforming data...")
    clean_tickets = cleaner.clean_tickets(raw_tickets)
    clean_history = cleaner.clean_history(raw_history)
    
    calculator = MetricsCalculator()
    print("3. Calculating metrics...")
    overall_metrics = calculator.calculate_volume_and_times(clean_tickets)
    sla_metrics = calculator.calculate_sla_compliance(clean_tickets)
    
    frt_df = calculator.calculate_first_response_time(clean_history)
    overall_metrics['avg_first_response_time_hrs'] = float(frt_df['frt_hours'].mean()) if not frt_df.empty else 0.0
    
    cat_prio_df = calculator.aggregate_by_category_and_priority(clean_tickets)
    agent_df = calculator.aggregate_by_agent(clean_tickets)
    
    print("4. Saving analytical outputs...")
    # Export datasets
    clean_tickets.to_csv("outputs/analytical_tickets.csv", index=False)
    frt_df.to_csv("outputs/first_response_times.csv", index=False)
    cat_prio_df.to_csv("outputs/tickets_by_category_priority.csv", index=False)
    agent_df.to_csv("outputs/tickets_by_agent.csv", index=False)
    
    # Export high-level metrics JSON
    dashboard_metrics = {
        **overall_metrics,
        **sla_metrics
    }
    
    with open("outputs/dashboard_metrics.json", "w") as f:
        json.dump(dashboard_metrics, f, indent=4)
        
    print("✅ Pipeline finished! Outputs generated at analytics/outputs/")

if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs"), exist_ok=True)
    run_pipeline()
