import pandas as pd
import numpy as np

class MetricsCalculator:
    @staticmethod
    def calculate_volume_and_times(tickets_df: pd.DataFrame):
        total_tickets = len(tickets_df)
        resolved_tickets = tickets_df[tickets_df['is_resolved']]
        
        avg_res_time = resolved_tickets['resolution_time_hours'].mean()
        med_res_time = resolved_tickets['resolution_time_hours'].median()
        
        return {
            'total_volume': total_tickets,
            'resolved_volume': len(resolved_tickets),
            'avg_resolution_time_hrs': float(avg_res_time) if not pd.isna(avg_res_time) else 0.0,
            'median_resolution_time_hrs': float(med_res_time) if not pd.isna(med_res_time) else 0.0
        }
        
    @staticmethod
    def calculate_sla_compliance(tickets_df: pd.DataFrame) -> dict:
        resolved = tickets_df[tickets_df['is_resolved']].copy()
        if len(resolved) == 0:
            return {'compliance_rate_percent': 0, 'breached_tickets': 0, 'met_sla_tickets': 0}
            
        # SLA breach check
        resolved['sla_breached'] = resolved['resolution_time_hours'] > resolved['sla_limit']
        
        breach_count = resolved['sla_breached'].sum()
        total_resolved = len(resolved)
        compliance_rate = ((total_resolved - breach_count) / total_resolved) * 100
        
        return {
            'compliance_rate_percent': float(compliance_rate),
            'breached_tickets': int(breach_count),
            'met_sla_tickets': int(total_resolved - breach_count)
        }

    @staticmethod
    def calculate_first_response_time(history_df: pd.DataFrame) -> pd.DataFrame:
        if history_df.empty:
            return pd.DataFrame(columns=['ticket_id', 'opened_at', 'first_response_at', 'frt_hours'])
            
        history_sorted = history_df.sort_values(['ticket_id', 'changed_at'])
        
        new_times = history_sorted[history_sorted['status'] == 'New'].groupby('ticket_id')['changed_at'].min().reset_index()
        new_times.rename(columns={'changed_at': 'opened_at'}, inplace=True)
        
        in_prog_times = history_sorted[history_sorted['status'] == 'In Progress'].groupby('ticket_id')['changed_at'].min().reset_index()
        in_prog_times.rename(columns={'changed_at': 'first_response_at'}, inplace=True)
        
        frt_df = pd.merge(new_times, in_prog_times, on='ticket_id', how='inner')
        frt_df['frt_hours'] = (frt_df['first_response_at'] - frt_df['opened_at']).dt.total_seconds() / 3600
        
        return frt_df

    @staticmethod
    def aggregate_by_category_and_priority(tickets_df: pd.DataFrame) -> pd.DataFrame:
        return tickets_df.groupby(['category_name', 'priority']).size().reset_index(name='count')
        
    @staticmethod
    def aggregate_by_agent(tickets_df: pd.DataFrame) -> pd.DataFrame:
        return tickets_df.groupby('agent_name').size().reset_index(name='tickets_handled')
