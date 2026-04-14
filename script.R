# =========================
# IT Support Ticket Analysis
# =========================

# Clean environment
rm(list = ls())

# Set working directory automatically (RProj)

# 📦 Load libraries
library(tidyverse)
library(lubridate)

# 📂 Load dataset
data <- read.csv("data/tickets.csv")

# 🔧 Data preparation
data <- data %>%
  mutate(
    date_opened = as.Date(date_opened),
    priority = factor(priority, levels = c("Low", "Medium", "High"))
  )

# =========================
# 📊 ANALYSIS
# =========================

# 🔹 Tickets by category
tickets_by_category <- data %>%
  count(category)

ggplot(tickets_by_category, aes(x = category, y = n, fill = category)) +
  geom_col() +
  labs(title = "Tickets by Category")

ggsave("charts/tickets_by_category.png")

# 🔹 Resolution time by priority
resolution_time <- data %>%
  group_by(priority) %>%
  summarise(avg_time = mean(resolution_time_hours))

ggplot(resolution_time, aes(x = priority, y = avg_time, fill = priority)) +
  geom_col() +
  labs(title = "Resolution Time by Priority")

ggsave("charts/resolution_time_by_priority.png")

# 🔹 Top issues
top_issues <- data %>%
  count(issue_type, sort = TRUE)

ggplot(top_issues, aes(x = reorder(issue_type, n), y = n)) +
  geom_col(fill = "steelblue") +
  coord_flip() +
  labs(title = "Top Issues")

ggsave("charts/top_issues.png")

# =========================
# ✅ END OF SCRIPT
# =========================