# EconoCausal: Dynamic Pricing via Double Machine Learning

This is the frontend application for the **EconoCausal** project. It provides an interactive dashboard for marketing directors to visualize causal treatment effects, analyze customer segments, and optimize discount allocation using Double Machine Learning (DML).

## 🚀 Features Built
- **Overview Dashboard:** Displays the core business metrics, a custom `ExecutiveSummary` component translating ML results into plain language, and the interactive Plotly **Uplift Curve** (proving the Causal Model outperforms random targeting).
- **Data Upload:** A fully functional drag-and-drop CSV uploader that connects to the FastAPI backend, with loading states and error handling.
- **Exploratory Data Analysis (EDA):** A dynamic analysis page that fetches backend data to render KPI cards, treatment group distributions, and a correlation matrix.
- **Allocation Matrix:** A prescriptive table showing the optimal discount assignment for specific user segments (e.g., "Persuadable" vs. "Sure Thing").
- **User Experience:** Custom error boundaries and empty states (e.g., graceful fallback when the backend is disconnected).

## 🛠️ Tech Stack
- **Framework:** React 18 (powered by Vite)
- **Routing:** React Router DOM
- **Data Visualization:** Plotly.js (`react-plotly.js`)
- **Styling:** Custom CSS with CSS Variables for a consistent design system
- **API Integration:** Fetch API connecting to a local FastAPI server (`http://localhost:8000`)

## 💻 How to Run Locally

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend