CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE sla_policies (
    id SERIAL PRIMARY KEY,
    priority VARCHAR(20) UNIQUE NOT NULL,
    max_resolution_time_hours NUMERIC NOT NULL
);

CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    agent_id INTEGER REFERENCES agents(id),
    category_id INTEGER REFERENCES categories(id) NOT NULL,
    sla_policy_id INTEGER REFERENCES sla_policies(id),
    issue_type VARCHAR(100) NOT NULL,
    operating_system VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'New',
    date_opened TIMESTAMP NOT NULL,
    date_resolved TIMESTAMP,
    resolution_time_hours NUMERIC
);

CREATE TABLE ticket_status_history (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMP NOT NULL,
    changed_by_agent_id INTEGER REFERENCES agents(id)
);

-- Indexes for performance
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_opened ON tickets(date_opened);
CREATE INDEX idx_tickets_category ON tickets(category_id);
CREATE INDEX idx_tickets_sla ON tickets(sla_policy_id);
