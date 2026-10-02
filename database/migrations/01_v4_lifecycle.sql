-- SupportOps V4: ticket lifecycle support
-- Adds columns required by the FastAPI models. Idempotent.

ALTER TABLE agents ADD COLUMN IF NOT EXISTS active INTEGER NOT NULL DEFAULT 1;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS description TEXT;

ALTER TABLE tickets ADD COLUMN IF NOT EXISTS description TEXT;

ALTER TABLE ticket_status_history ADD COLUMN IF NOT EXISTS note TEXT;

-- Speeds up the filters exposed by GET /tickets
CREATE INDEX IF NOT EXISTS idx_tickets_agent ON tickets(agent_id);
CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_history_ticket ON ticket_status_history(ticket_id, changed_at);