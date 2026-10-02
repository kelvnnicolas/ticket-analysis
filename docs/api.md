# SupportOps API (V3 + V4)

API REST do SupportOps: operações de tickets, ciclo de vida ITSM com máquina de
estados, motor de SLA e métricas analíticas calculadas ao vivo sobre PostgreSQL.

## Como rodar

```bash
# 1. Banco de desenvolvimento (porta 5435) e banco de testes (5436)
docker compose up -d

# 2. Dependências Python
backend/venv/bin/pip install -r backend/requirements.txt

# 3. API
cd <repo-root>
DATABASE_URL="postgresql://supportops:password@localhost:5435/supportops" \
  backend/venv/bin/uvicorn backend.app.main:app --reload --port 8010
```

Documentação interativa: `http://localhost:8010/docs`

## Configuração

Todas as variáveis são lidas por `backend/app/config.py` (pydantic-settings) e
aceitam prefixo em maiúsculas. As mais relevantes:

| Variável | Default | Descrição |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://supportops:password@localhost:5435/supportops` | Conexão do SQLAlchemy |
| `SQL_ECHO` | `false` | Loga o SQL emitido |
| `DEFAULT_PAGE_SIZE` | `50` | Tamanho de página padrão |
| `MAX_PAGE_SIZE` | `200` | Limite de `page_size` |
| `CORS_ORIGINS` | `*` | Origens permitidas (separadas por vírgula) |

Variáveis também podem ser fornecidas via `.env` na raiz do projeto.

## Ciclo de vida do ticket

Fluxo canônico definido em `backend/app/services/lifecycle.py`:

```
New -> Assigned -> In Progress -> Resolved -> Closed
```

Reabertura é permitida (`Resolved`/`Closed` -> `In Progress`) e limpa o carimbo
de resolução. Transições fora da tabela retornam **409 Conflict**. O estado atual
de um ticket pode ser consultado em `GET /tickets/{id}/transitions`.

## Motor de SLA

`backend/app/services/sla.py` classifica cada ticket:

| Estado | Significado |
| --- | --- |
| `on_track` | Aberto, menos de 80% do prazo consumido |
| `at_risk` | Aberto, 80% ou mais do prazo consumido |
| `breached` | Aberto e vencido, ou resolvido após o prazo |
| `met` | Resolvido dentro do prazo |
| `no_policy` | Sem política de SLA vinculada |

O filtro `?sla_state=` usa uma expressão SQL equivalente (`sla_state_expression`)
a fim de manter listagem e contagem em paridade com a avaliação em memória —
há teste cobrindo essa equivalência.

## Tickets

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/tickets/` | Listagem paginada com filtros |
| GET | `/tickets/{id}` | Detalhe, incluindo bloco `sla` |
| GET | `/tickets/{id}/history` | Histórico de status ordenado |
| GET | `/tickets/{id}/transitions` | Transições permitidas a partir do status atual |
| GET | `/tickets/{id}/sla` | Avaliação de SLA isolada |
| POST | `/tickets/` | Cria ticket (registra status inicial no histórico) |
| PATCH | `/tickets/{id}` | Atualiza campos e/ou status |
| DELETE | `/tickets/{id}` | Remove ticket **resolved ou closed** (409 caso contrário) |

### Filtros de `GET /tickets/`

`status`, `category_id`, `agent_id`, `customer_id`, `priority`, `sla_state`,
`search` (issue_type/description/operating_system), `opened_from`, `opened_to`
(ISO-8601), `sort_by` (`id`, `date_opened`, `date_resolved`, `status`,
`issue_type`, `resolution_time_hours`), `sort_dir`, `page`, `page_size`.

Resposta:

```json
{
  "total": 201,
  "page": 1,
  "page_size": 50,
  "items": [
    {
      "id": 201,
      "issue_type": "Email not working",
      "category": "Software",
      "agent": "John Support",
      "status": "In Progress",
      "date_opened": "2026-09-24T03:20:42",
      "resolution_time_hours": null,
      "sla_state": "breached",
      "sla_due_at": "2026-09-25T03:20:42"
    }
  ]
}
```

### Criação

`priority` é um atalho que resolve a `sla_policies` correspondente; `sla_policy_id`
prevalece quando enviado. Referências inexistentes retornam **422**.

```bash
curl -X POST localhost:8010/tickets/ \
  -H 'Content-Type: application/json' \
  -d '{"issue_type":"VPN drop","category_id":1,"priority":"High","agent_id":1,"customer_id":1}'
```

### Transição de status

```bash
curl -X PATCH localhost:8010/tickets/202 \
  -H 'Content-Type: application/json' \
  -d '{"status":"Resolved","note":"Reconfigurado no roteador"}'
```

A primeira transição para `Resolved`/`Closed` carimba `date_resolved` e
`resolution_time_hours`; a reabertura limpa ambos os campos. Toda mudança de
status gera uma linha em `ticket_status_history` com `changed_by_agent_id` e a
nota opcional.

## Entidades

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/customers` | Lista com paginação |
| GET | `/agents` | Lista; `?active_only=true` filtra agentes ativos |
| GET | `/categories` | Lista completa |
| GET | `/sla-policies` | Políticas ordenadas por limite |
| GET | `/entities/counts` | Contagem por entidade |
| GET | `/agents/{id}/workload` | Carga, tickets abertos, violações e tempo médio |

## Analytics

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/analytics/overview` | Volume, tempos (avg/median/p90), FRT, compliance, status |
| GET | `/analytics/by-category` | Volume e tempo médio por categoria |
| GET | `/analytics/by-priority` | Volume por prioridade com limite de SLA |
| GET | `/analytics/by-agent` | Volume por agente |
| GET | `/analytics/sla-compliance` | Compliance por prioridade |
| GET | `/analytics/backlog` | Tickets abertos com urgência e `remaining_hours` |
| GET | `/analytics/trend` | Abertura e resolução por dia |
| GET | `/analytics/pipeline-report` | Métricas em lote do pipeline Python |

`/overview` e as demais rotas computam sobre o banco em tempo real; o
`/pipeline-report` expõe o JSON gerado offline por `analytics/pipeline.py`,
útil para comparar o batch com o cálculo on-line.

## Sistema

- `GET /ui` — painel operacional (V5), servido pela própria API
- `GET /health` — verifica o banco; retorna **503** com `status: degraded` se a
  conexão falhar.
- `GET /` — identificação do serviço.

## Painel operacional (V5)

`GET /ui` entrega uma interface web em HTML/CSS/JavaScript puro, sem build step
e sem dependência externa de CDN. Os gráficos são SVG desenhados em
`app.js`, o que evita depender de rede ou de bibliotecas de terceiros.

Arquivos em `backend/app/static/`:

- `index.html` — estrutura das três visões (Dashboard, Tickets, Novo incidente)
- `styles.css` — tema escuro, responsivo, badges de status e SLA
- `app.js` — consumo da API, renderização dos gráficos e ações

Funcionalidades:

- **Dashboard** — seis KPIs (volume, conformidade SLA, tempo médio, P90,
  primeira resposta, backlog vencido), gráficos de volume por categoria,
  conformidade por prioridade, série temporal de abertura/resolução e carga por
  agente, além do backlog ordenado por urgência de SLA.
- **Tickets** — tabela paginada com filtros por status, prioridade, situação
  SLA, categoria, agente e busca textual.
- **Novo incidente** — formulário de registro manual e painel de detalhe com
  histórico de status em linha do tempo.
- **Transição de status** — modal que consulta `GET /tickets/{id}/transitions` e
  oferece apenas as transições válidas para o estado atual.

O painel opera em modo leitura/escrita sobre a mesma API documentada acima; não
há camada de autenticação, então deve permanecer em ambiente local até V8.

## Testes

```bash
docker compose up -d db-test
backend/venv/bin/python -m pytest backend/tests -c backend/pytest.ini
```

Os testes usam o banco `supportops_test` na porta 5436 e cobrem a máquina de
estados, o motor de SLA, o CRUD de tickets, entidades e as rotas analíticas.

## Estrutura

```
backend/app/
├── main.py          # app, lifespan, health, CORS
├── config.py        # settings (pydantic-settings)
├── database.py      # engine + SessionLocal + get_db
├── models.py        # ORM SupportOps
├── schemas.py       # contratos Pydantic
├── crud.py          # acesso a dados e regras de escrita
├── routes/
│   ├── tickets.py
│   ├── entities.py
│   └── analytics.py
├── services/
│   ├── lifecycle.py # tabela de transições de status
│   └── sla.py       # avaliação de SLA (memória e SQL)
└── static/          # painel operacional (V5)
    ├── index.html
    ├── styles.css
    └── app.js
```