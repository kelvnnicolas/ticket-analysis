# SupportOps Data Model (V1)

## Entidades e Relacionamentos

A modelagem de dados foi desenhada para transformar o dataset histórico estático em um sistema transacional capaz de suportar um fluxo ITSM (Information Technology Service Management) real.

### 1. `customers` (Clientes/Solicitantes)
Representa os usuários que abrem os tickets. No dataset original não existiam, então foram adicionados para suportar o processo transacional.
- `id` (PK, Serial)
- `name` (Varchar)
- `email` (Varchar, Unique)

### 2. `agents` (Agentes de Suporte)
Representa os analistas que resolveem os tickets.
- `id` (PK, Serial)
- `name` (Varchar)
- `email` (Varchar, Unique)

### 3. `categories` (Categorias)
Extraídas do dataset original (`Network`, `Hardware`, `Software`, `Access`).
- `id` (PK, Serial)
- `name` (Varchar, Unique)

### 4. `sla_policies` (Políticas de SLA)
Define o tempo limite de resolução baseado na prioridade.
- `id` (PK, Serial)
- `priority` (Varchar, Unique) - `Low`, `Medium`, `High`
- `max_resolution_time_hours` (Numeric)

### 5. `tickets` (Incidentes/Chamados)
Tabela principal que armazena os chamados. Expandida para suportar status e FKs.
- `id` (PK, Serial)
- `customer_id` (FK -> customers.id)
- `agent_id` (FK -> agents.id)
- `category_id` (FK -> categories.id)
- `sla_policy_id` (FK -> sla_policies.id)
- `issue_type` (Varchar) - Ex: "Printer Error", "VPN Issue"
- `operating_system` (Varchar) - Ex: "Windows", "Linux", "macOS"
- `status` (Varchar) - `New`, `Assigned`, `In Progress`, `Resolved`, `Closed`
- `date_opened` (Timestamp)
- `date_resolved` (Timestamp, Nullable)
- `resolution_time_hours` (Numeric, Nullable)

### 6. `ticket_status_history` (Histórico de Status)
Registra as mudanças de estado do ticket ao longo do tempo (Life Cycle).
- `id` (PK, Serial)
- `ticket_id` (FK -> tickets.id)
- `status` (Varchar)
- `changed_at` (Timestamp)
- `changed_by_agent_id` (FK -> agents.id, Nullable)

## Índices e Constraints Principais
- **Primary Keys:** Definidas com `SERIAL` (`id`).
- **Foreign Keys:**
  - `tickets.category_id` (Obrigatório)
  - `ticket_status_history.ticket_id` (Com `ON DELETE CASCADE`)
- **Índices sugeridos:**
  - `CREATE INDEX idx_tickets_status ON tickets(status);`
  - `CREATE INDEX idx_tickets_opened ON tickets(date_opened);`

## Transição V0 -> V1
Os dados do arquivo `data/tickets.csv` foram preservados.
Durante a etapa de Seed:
1. Foram criados "Mock Customers" e "Mock Agents".
2. Categorias e SLAs foram inseridos dinamicamente baseados nos dados existentes.
3. Os 200 tickets originais foram importados. Como os tickets da V0 já estão concluídos, todos recebem o status `Closed`. O tempo de resolução e data de fechamento foram mantidos/calculados para manter a fidelidade histórica.
