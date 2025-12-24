# NYX DATA VALIDATOR 

> **AI-Assisted Data Validation Platform**  
> Deterministic validation powered by intelligent root cause analysis

![Status](https://img.shields.io/badge/status-production--ready-brightgreen) ![Python](https://img.shields.io/badge/python-3.12-blue) ![React](https://img.shields.io/badge/react-18-blue) ![FastAPI](https://img.shields.io/badge/fastapi-latest-green)

---

## 🎯 What is Nyx?

Nyx Data Validator is an enterprise-grade web application that **validates Growth CSV data against Fabric Gold warehouse data**, automatically identifies root causes of mismatches, and provides AI-powered explanations with actionable fix suggestions.

### Key Capabilities

✅ **6-Layer Deterministic Validation** (Overall, Date, Campaign, Gender, Age, Campaign+Date)  
🤖 **AI-Powered Insights** via Google Gemini 2.5 Flash/3.0 Pro  
🔍 **Automatic Root Cause Detection** (5 rule-based engines)  
🛠️ **Fix Suggestions** (Copy-paste Pandas/SQL code)  
📊 **Premium Dashboard UI** (Glassmorphism + Interactive Charts)  
🔗 **Smart Column Mapping** (Fuzzy + Semantic matching)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Google Gemini API Key ([Get one here](https://aistudio.google.com/app/apikey))

### Installation

```bash
# 1. Clone/navigate to project
cd advanced_data_validator

# 2. Install backend dependencies
cd backend
py -m pip install -r requirements.txt

# 3. Setup environment variables
copy .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 4. Install frontend dependencies
cd ../frontend
npm install

# 5. Launch the application
cd ..
py run_app.py
```

### Access the App
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

---

## 📐 Architecture

```
┌─────────────────────┐
│  React Frontend     │  ← Glassmorphism UI, Chart.js
│  (Vite + Lucide)    │
└──────────┬──────────┘
           │ REST API
┌──────────▼──────────┐
│  FastAPI Backend    │
├─────────────────────┤
│ ┌─────────────────┐ │
│ │ Column Mapper   │ │  ← Fuzzy + Semantic
│ └─────────────────┘ │
│ ┌─────────────────┐ │
│ │ Validator Engine│ │  ← 6-layer validation
│ └─────────────────┘ │
│ ┌─────────────────┐ │
│ │ Root Cause Eng. │ │  ← 5 deterministic rules
│ └─────────────────┘ │
│ ┌─────────────────┐ │
│ │ Fix Suggester   │ │  ← Pandas/SQL fixes
│ └─────────────────┘ │
│ ┌─────────────────┐ │
│ │ Gemini AI       │ │  ← Natural language summaries
│ └─────────────────┘ │
└─────────────────────┘
```

---

## 🧠 Intelligence Features

### Phase 1-5: Data Processing
- **Auto Column Mapping**: 85%+ accuracy with fuzzy matching
- **6-Layer Validation**: From high-level totals to granular campaign+date

### Phase 6: Root Cause Detection
Automatically identifies:
1. 🔄 **Duplicate Records** → Growth CSV contains repeated rows
2. 📏 **Grain Mismatch** → Different aggregation levels
3. 📅 **Date Shift** → Timezone or lag issues
4. 🏷️ **Missing Campaigns** → Campaigns in one source but not the other
5. 📈 **Systematic Bias** → One source consistently higher

### Phase 7: Fix Suggestions
For each root cause, Nyx generates:
- **Pandas Code**: Copy-paste ready Python fixes
- **SQL Equivalent**: For warehouse teams
- **Prevention Tips**: How to avoid in the future

### Phase 8: Gemini AI Assistant
- **Executive Summaries**: High-level insights for stakeholders
- **Natural Language Explanations**: Plain English interpretations
- **Interactive Q&A**: Ask questions about your data

---

## 📊 Example Output

```
ROOT CAUSE: Duplicate Records
Confidence: 95%
Evidence: Growth CSV contains 147 duplicate rows

FIX (Pandas):
growth_df_clean = growth_df.drop_duplicates()
print(f"Removed {len(growth_df) - len(growth_df_clean)} duplicates")

PREVENTION:
Add DISTINCT clause to extraction query in ETL pipeline
```

---

## 🔐 Environment Variables

Create a `.env` file in the `backend` directory:

```env
GOOGLE_API_KEY=AIzaSy...your_key_here
```

---

## 🛡️ Enterprise Features

- **Audit Trail**: Every validation is timestamped and reproducible
- **Data Lineage**: Track validation configurations
- **Export Reports**: HTML + CSV downloads
- **Column Mapping UI**: Review and adjust auto-mappings

---

## 📚 Tech Stack

**Backend**
- FastAPI (Python web framework)
- Pandas (Data processing)
- Google Generative AI (Gemini 2.5/3.0)
- FuzzyWuzzy (Column matching)

**Frontend**
- React 18 + Vite
- Chart.js (Visualizations)
- Lucide Icons
- Vanilla CSS (Glassmorphism)

---

## 🎨 UI Preview

- **Dark Mode Glassmorphism** design
- **Interactive Data Grids** with search, sort, pagination
- **Multi-Chart Dashboards** (Bar, Radar, Trend lines)
- **AI Chat Panel** for conversational insights

---

## 📖 Documentation

- [Implementation Plan](./implementation_plan.md)
- [API Documentation](http://localhost:8000/docs) (when running)
- [Task Tracking](./task.md)

---

## 🤝 Contributing

This is a production system for data validation. For feature requests or bugs, create detailed issues with:
- CSV sample data
- Expected vs actual behavior
- Error logs (if applicable)

---

## 📄 License

Proprietary - Internal Use Only

---

**Built with ❤️ for Data Quality Teams**
