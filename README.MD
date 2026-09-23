# 📊 IT Support Ticket Analysis

Data Analysis project focused on IT Support operations, exploring incident patterns, resolution efficiency, and opportunities for process optimization.

---

## 🚀 Project Overview

This project simulates a real-world IT support environment and applies data analysis techniques to understand ticket behavior and operational performance.

The analysis was developed using R and RStudio, with a focus on reproducibility and structured workflows.

---

## 🧠 Objectives

- Analyze ticket distribution across categories  
- Evaluate resolution time by priority  
- Identify recurring issues  
- Generate actionable insights for process improvement  

---

## 📂 Dataset

A simulated dataset of IT support tickets was created and stored in:

--> data/tickets.csv

Main variables:
- category  
- priority  
- issue_type  
- operating_system  
- resolution_time_hours  

---

## 🛠 Tools & Technologies

- R  
- RStudio  
- tidyverse (dplyr, ggplot2)  
- lubridate  

---

## ▶️ How to Run

1. Open the `.Rproj` file in RStudio  
2. Run the script:

--> script.R


3. Output charts will be automatically generated in:
/charts/


---

## 📊 Analysis Performed

- Ticket volume by category  
- Resolution time by priority  
- Recurring issues ranking  
- Resolution time distribution  

---

## 📈 Key Insights

- Software-related issues represent the majority of incidents  
- High-priority tickets require longer resolution time  
- A small number of recurring issues drives a large portion of tickets  

---

## 💡 Recommendations

- Automate repetitive issues (e.g., password resets)  
- Improve knowledge base documentation  
- Optimize ticket triage processes  

---

## 📁 Project Structure

ticket-analysis/
├── data/
├── charts/
├── script.R
├── README.md
└── ticket-analysis.Rproj



---

## 🎯 Skills Demonstrated

- Data Analysis  
- Data Visualization  
- Exploratory Data Analysis (EDA)  
- Statistical Thinking  
- Business Insight Generation  

---

## 🌍 Context

This project reflects the transition from IT Support to Data Analysis, combining technical experience with data-driven decision-making.

---

## 📬 Contact

Open to opportunities in Data Analysis, Business Intelligence, and Technical/Data hybrid roles.

---

## 🚀 Evolution Roadmap (SupportOps)

This project is currently being evolved progressively into a full-stack ITSM & Analytics platform named **SupportOps**, moving from static CSV data analysis to a robust production-ready API and intelligent automation.

### Current Progress

- [x] **V0: Data Analysis (Baseline)** - Original R/RStudio analysis and EDA.
- [x] **V1: Data Model + PostgreSQL** - Migrated historical dataset into a relational database with ITSM principles (SLAs, Agents, History).
- [x] **V2: Python + Pandas Analytics Pipeline** - Automated ETL generating advanced ITSM metrics (SLA Compliance, First Response Time, Volume, Aggregations).
- [ ] **V3: FastAPI / Backend** - RESTful API for ticket and operations management.
- [ ] **V4: ITSM + Ticket Lifecycle + SLA** - Transition logic, SLA breached engines.
- [ ] **V5: Operational Dashboard** - UI for Analytics and Ticket operations.
- [ ] **V6: Automation** - n8n workflows for notifications and proactive alerts.
- [ ] **V7: AI-Assisted Support** - LLM-powered ticket classification and resolution suggestion.
- [ ] **V8: Production Readiness** - Testing, Dockerization, CI/CD.
