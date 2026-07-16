# 📊 AdventureWorks Commercial Intelligence Suite

An interactive, multipage **Decision Support System (DSS)** built to help Commercial, Sales, Finance, and Country Managers track performance, diagnose risks, and simulate strategic decisions — all in one place.

## 🚀 Live Application

👉 [Open the Live Dashboard](https://adventureworks-commercial-dashboard.streamlit.app/)

---

## 📌 Project Overview

This project models a centralized commercial cockpit on top of an AdventureWorks-style sales data structure (Products, Customers, Territories, Sales, Returns). Instead of only displaying charts, the system actively diagnoses operational issues — such as high-volume/low-margin products or elevated return rates — forecasts revenue, and generates dynamic strategic recommendations.

> **Note on data:** The current version generates a synthetic dataset in code (seeded for reproducibility) that follows the AdventureWorks schema and business logic. This was a deliberate choice to iterate quickly on the analytics logic and UI without depending on external files. A future iteration will connect directly to the original AdventureWorks dataset.

### Key Features by Page

1. **📊 Executive Summary** — Dynamic KPI tracking (Revenue, Gross Margin, Order Volume, Return Rate) with a proactive Quick Diagnostic Tool that flags operational issues.
2. **🛍️ Sales Performance** — Category performance (Revenue vs. Net Profit), regional market share, and top 10 products/customers.
3. **💸 Profitability & Returns** — A Volume vs. Margin Quadrant Analysis that classifies products as "Problem Stars" or "Niche Champions," paired with a financial leakage audit of returns.
4. **🔮 Forecasting & Strategy** — A 12-month linear trend forecast combined with an automated recommendation engine that surfaces strategic insights.
5. **🎛️ Scenario Simulation** — An interactive "What-If" tool letting managers adjust price, volume, and return-rate levers to preview the direct bottom-line impact.

---

## 🎯 Why I Built This

I built this project to demonstrate how I think about commercial data as a business problem, not just a visualization exercise: identifying margin leakage, quantifying the impact of pricing and volume decisions, and translating raw transactional data into decisions a manager can act on. It reflects the kind of analytical thinking I'd like to bring to Siemens' Commercial team.

---

## 🛠️ Technology Stack

- **Python** — data wrangling and modeling
- **Streamlit** — multipage web application framework
- **Plotly Express & Graph Objects** — interactive financial visualizations
- **Pandas & NumPy** — data integration and statistical calculations

---

## 💻 Local Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/tubaakeskin/adventureworks-commercial-dashboard.git
cd adventureworks-commercial-dashboard
pip install -r requirements.txt
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## 🔭 Roadmap

- [ ] Connect to the real AdventureWorks dataset instead of synthetic data
- [ ] Replace the linear trend forecast with a seasonality-aware model
- [ ] Split `app.py` into modules (data loading, metrics, pages)
- [ ] Add unit tests for the metric calculations

---

## 📬 Contact

Tuba Akeskin — [GitHub](https://github.com/tubaakeskin)
