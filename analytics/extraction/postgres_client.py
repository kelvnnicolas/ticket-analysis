import pandas as pd
from sqlalchemy import create_engine

class PostgresExtractor:
    def __init__(self, db_url="postgresql://supportops:password@localhost:5435/supportops"):
        self.engine = create_engine(db_url)
        
    def extract_tickets_with_context(self):
        query = """
            SELECT 
                t.id as ticket_id,
                t.issue_type,
                t.operating_system,
                t.status,
                t.date_opened,
                t.date_resolved,
                t.resolution_time_hours,
                c.name as category_name,
                a.name as agent_name,
                s.priority,
                s.max_resolution_time_hours as sla_limit
            FROM tickets t
            JOIN categories c ON t.category_id = c.id
            JOIN agents a ON t.agent_id = a.id
            JOIN sla_policies s ON t.sla_policy_id = s.id
        """
        return pd.read_sql(query, self.engine)

    def extract_ticket_history(self):
        query = """
            SELECT 
                ticket_id,
                status,
                changed_at,
                changed_by_agent_id
            FROM ticket_status_history
            ORDER BY ticket_id, changed_at ASC
        """
        return pd.read_sql(query, self.engine)
