# Métricas de Suporte e SLA (SupportOps V2)

Este documento descreve as métricas implementadas no pipeline de Analytics (Python/Pandas). 
Estas métricas estendem a versão legada em R e são alimentadas diretamente do banco PostgreSQL, fornecendo contexto para a camada ITSM (Escada 4) e dashboards.

## 1. Ticket Volume
- **Descrição:** Contagem total de tickets abertos em determinado período.
- **Utilidade:** Entendimento de carga, sazonalidade e dimensionamento da equipe.
- **Cálculo:** `COUNT(tickets)` agrupados ou no geral.

## 2. Average / Median Resolution Time
- **Descrição:** Tempo (em horas) entre a data de abertura e a data de resolução final.
- **Utilidade:** Mede a eficiência do suporte em resolver os problemas reportados de forma geral e isolando outliers (via mediana).
- **Cálculo:** `AVG(resolution_time_hours)`, `MEDIAN(resolution_time_hours)`. O tempo é extraído de `date_resolved - date_opened`.

## 3. First Response Time (FRT)
- **Descrição:** Tempo entre a abertura (`New`) e o primeiro registro de atendimento (`In Progress`).
- **Utilidade:** Mostra quão rápido a equipe pega os chamados para trabalhar, vital para a experiência do usuário.
- **Cálculo:** Diferença de tempo no `ticket_status_history` entre o registro de `New` e o de `In Progress`.

## 4. SLA Compliance
- **Descrição:** Percentual de tickets resolvidos dentro ou fora do SLA estipulado (baseado na política de SLA vinculada à prioridade).
- **Utilidade:** Indicador mais importante de acordo de níveis de serviço, mostra qualidade e eficiência perante o cliente.
- **Cálculo:** Contagem de tickets onde `resolution_time_hours <= sla_policies.max_resolution_time_hours` dividido pelo Total de Tickets * 100.

## 5. Tickets by Category & Priority
- **Descrição:** Volume particionado.
- **Utilidade:** Identifica gargalos (Ex: muitos chamados de Hardware de Alta prioridade).
- **Cálculo:** Agrupamento por categoria e prioridade.

## 6. Tickets by Agent
- **Descrição:** Carga de trabalho alocada ou resolvida por analista.
- **Utilidade:** Ajuda a medir a distribuição e sobrecarga na operação de TI.
- **Cálculo:** `COUNT(tickets)` agrupados por `agent_id/agent.name`.

## Nota sobre o Backlog
Atualmente, por o log ser histórico, todos os incidentes originais já encontram-se concluídos (`Closed`). O "Backlog" de incidentes não resolvidos no momento em que o código roda é 0. O pipeline implementa a funcionalidade para calcular tickets abertos, mas a métrica demonstrará o valor do passado (se fatiada no tempo) ou zero, refletindo a natureza da V0.
