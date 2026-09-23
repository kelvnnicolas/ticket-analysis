# Project Audit - SupportOps (V0 Baseline)

## 1. Estado Atual e Arquitetura
O repositório atual (`ticket-analysis`) encontra-se na versão **V0 (camada histórica de Data Analysis)**.
Foi criado originalmente como uma demonstração de habilidades em R/RStudio focada em análise exploratória de um ambiente de suporte de TI.

**Estrutura de Diretórios atual:**
- `data/` (Contém o dataset `tickets.csv`)
- `charts/` (Contém gráficos em formato .png gerados pelo R)
- `script.R` (Script principal que executa a análise exploratória)
- `README.MD` (Documentação do projeto de Data Analysis)
- `ticket-analysis.Rproj` (Arquivo de configuração do RStudio)

**Fluxo de Dados Atual:**
Dataset local CSV (`data/tickets.csv`) -> R (tidyverse, lubridate) -> Visualizações em PNG (`charts/`)

**Dependências atuais:**
- Linguagem R
- Pacotes R: `tidyverse` (`dplyr`, `ggplot2`), `lubridate`

## 2. Dados Existentes
O projeto usa um arquivo de dados tabulares estruturados simulando um log de incidentes fechados.
- **Tamanho do Dataset:** 200 registros.
- **Valores Ausentes:** 0.
- **Colunas e Tipos:**
  - `ticket_id` (Inteiro, único para cada ticket)
  - `date_opened` (String de Data no formato `YYYY-MM-DD`)
  - `category` ("Network", "Hardware", "Software", "Access")
  - `priority` ("Low", "Medium", "High")
  - `issue_type` ("Printer Error", "Password Reset", "VPN Issue", "Slow Performance")
  - `operating_system` ("Linux", "Windows", "macOS")
  - `resolution_time_hours` (Numérico contínuo, de 1.10 a 71.50)

## 3. Métricas Analíticas Existentes
O script original em R (`script.R`) calcula e gera visualizações para:
- **Volume de Tickets por Categoria** (`tickets_by_category`)
- **Tempo Médio de Resolução por Prioridade** (`resolution_time`)
- **Ranking de Problemas Principais** (`top_issues`)

*(Nota: O README menciona "Resolution time distribution", mas o `script.R` não implementa nativamente, embora existam gráficos extras como `resolutiontime.png` no diretório `charts/` indicando testes locais prévios).*

## 4. Oportunidades, Problemas e O que Reutilizar

**O que Reutilizar:**
- Todo o dataset atual (`tickets.csv`) será utilizado como seed para as tabelas base.
- O script R deve ser preservado para garantir a reprodutibilidade original, validando os requisitos de não destruição do histórico.
- Os insights do README serão mantidos.

**Problemas / Limitações do Dataset Atual (Visão Operacional):**
- Ausência de SLA deadlines explícitos (tem apenas o tempo de resolução final).
- Não há informações de agentes assinalados (`assignee`), solicitantes (`requester`), canais e histórico de status. O log reflete tickets já concluídos de forma simplificada, necessitando evolução no Modelo de Dados relacional para simular um ambiente ITSM real transacional.

**Oportunidades e Plano Recomendado (Próximas Escadas):**
- **Escada 1 (Data Model):** Planejar esquema relacional PostgreSQL (`tickets`, `categories`, `agents`, `customers`, `sla_policies`). Realizar seed expandindo inteligentemente as lacunas atuais com base nos 200 tickets já existentes.
- **Escada 2 (Python/Pandas):** Migrar a responsabilidade do cálculo dessas 3 métricas base e adicionar novas exigidas usando Python em cima do Postgres.
- **Escada 3 (FastAPI):** Desenvolver API REST com base nas tabelas criadas.
- **Escadas Seguintes:** Implementar SLAs e Status, que trarão dinâmica transacional para o que hoje é um dataset estático, sem perder o registro histórico da V0.
