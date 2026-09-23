import csv
import random
from datetime import datetime, timedelta

def generate_seed_sql():
    sql = []
    sql.append("-- Seed Data Generated from data/tickets.csv")
    
    # 1. Customers
    customers = [
        "Alice Smith", "Bob Johnson", "Charlie Brown", "Diana Prince", "Evan Wright"
    ]
    sql.append("INSERT INTO customers (name, email) VALUES")
    customer_values = [f"('{name}', '{name.lower().replace(' ', '.')}@example.com')" for name in customers]
    sql.append(",\n".join(customer_values) + ";\n")
    
    # 2. Agents
    agents = [
        "John Support", "Jane Helpdesk", "Mike Admin"
    ]
    sql.append("INSERT INTO agents (name, email) VALUES")
    agent_values = [f"('{name}', '{name.lower().replace(' ', '.')}@supportops.com')" for name in agents]
    sql.append(",\n".join(agent_values) + ";\n")
    
    # 3. Categories
    categories = ["Network", "Hardware", "Software", "Access"]
    sql.append("INSERT INTO categories (name) VALUES")
    category_values = [f"('{c}')" for c in categories]
    sql.append(",\n".join(category_values) + ";\n")
    
    cat_map = {c: i+1 for i, c in enumerate(categories)}
    
    # 4. SLA Policies
    # Assuming standard hours: High=24, Medium=48, Low=72
    slas = [("High", 24), ("Medium", 48), ("Low", 72)]
    sql.append("INSERT INTO sla_policies (priority, max_resolution_time_hours) VALUES")
    sla_values = [f"('{p}', {h})" for p, h in slas]
    sql.append(",\n".join(sla_values) + ";\n")
    
    sla_map = {p: i+1 for i, (p, h) in enumerate(slas)}
    
    # 5. Tickets
    sql.append("INSERT INTO tickets (id, customer_id, agent_id, category_id, sla_policy_id, issue_type, operating_system, status, date_opened, date_resolved, resolution_time_hours) VALUES")
    
    ticket_values = []
    history_values = []
    
    with open('data/tickets.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = int(row['ticket_id'])
            
            # Generate random assignments
            customer_id = random.randint(1, len(customers))
            agent_id = random.randint(1, len(agents))
            
            category_id = cat_map[row['category']]
            sla_id = sla_map[row['priority']]
            issue_type = row['issue_type'].replace("'", "''")
            os = row['operating_system'].replace("'", "''")
            
            # Parse dates
            date_opened_str = row['date_opened'] + " 09:00:00" # default time
            date_opened = datetime.strptime(date_opened_str, "%Y-%m-%d %H:%M:%S")
            
            res_hours = float(row['resolution_time_hours'])
            date_resolved = date_opened + timedelta(hours=res_hours)
            
            status = 'Closed'
            
            val = f"({tid}, {customer_id}, {agent_id}, {category_id}, {sla_id}, '{issue_type}', '{os}', '{status}', '{date_opened}', '{date_resolved}', {res_hours})"
            ticket_values.append(val)
            
            # 6. Ticket Status History
            # For each ticket, we can simulate an opening, in progress and close
            history_values.append(f"({tid}, 'New', '{date_opened}', NULL)")
            
            in_prog_time = date_opened + timedelta(hours=res_hours * 0.1)
            history_values.append(f"({tid}, 'In Progress', '{in_prog_time}', {agent_id})")
            
            history_values.append(f"({tid}, 'Closed', '{date_resolved}', {agent_id})")
            
    sql.append(",\n".join(ticket_values) + ";\n")
    
    # Update tickets sequence
    sql.append("SELECT setval('tickets_id_seq', (SELECT MAX(id) FROM tickets));\n")
    
    # Insert History
    sql.append("INSERT INTO ticket_status_history (ticket_id, status, changed_at, changed_by_agent_id) VALUES")
    sql.append(",\n".join(history_values) + ";\n")
    
    with open('database/init/02_seed.sql', 'w') as f:
        f.write("\n".join(sql))
        
if __name__ == "__main__":
    generate_seed_sql()
    print("Seed file generated successfully at database/init/02_seed.sql")
