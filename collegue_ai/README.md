# Collegue AI — Prototype

Collegue AI is an offline-first planning assistant for ICT teachers in Moroccan middle schools. It helps teachers generate annual plans, unit plans, and sequence preparations aligned with official curricula.

## First Prototype Scope

- Clean official curriculum, calendar, and pedagogical memory data
- Generate annual planning for 1AC, 2AC, and 3AC (1st, 2nd, and 3rd year middle school)
- Display official units and sub-modules
- Display the official academic calendar
- Display the pedagogical planning framework
- AI-powered teaching assistant for Q&A

## Tech Stack

- **Backend**: Python, FastAPI
- **Frontend**: Streamlit
- **Data Storage**: JSON files (local offline storage)
- **AI/ML**: Local models for pedagogical assistance

## Project Structure

```
collegue_ai/
├── app/
│   ├── api/              # FastAPI backend routers
│   │   ├── main.py       # Main API application
│   │   ├── routers_ai.py     # AI assistant endpoints
│   │   ├── routers_dashboard.py # Dashboard endpoints
│   │   └── routers_grid.py   # Grid/data endpoints
│   └── frontend/         # Streamlit frontend
│       ├── Home.py       # Main page
│       ├── pages/        # Application pages
│       │   ├── 1_Planification_Annuelle.py
│       │   ├── 2_Planification_Unite.py
│       │   ├── 3_Preparation_Sequence.py
│       │   ├── 4_Calendrier.py
│       │   ├── 5_Parametres.py
│       │   ├── 6_Assistant_IA.py
│       │   └── 7_Modele_Annuel.py
│       ├── api_client.py # Backend API client
│       └── theme.py      # UI theme configuration
├── data/
│   ├── ai/               # AI model files and datasets
│   ├── plans/            # Generated teaching plans
│   │   ├── annual/       # Annual plans (AP-*.json)
│   │   ├── unit/         # Unit plans (UP-*.json)
│   │   └── sequence/     # Sequence plans (SEQ-*.json)
│   ├── raw/              # Raw input data
│   └── reference/        # Cleaned reference data
├── scripts/              # Data processing scripts
│   ├── build_pedago_model.py
│   ├── build_qa_dataset.py
│   ├── build_rag_index.py
│   ├── clean_reference_data.py
│   └── eval_assistant.py
├── requirements.txt      # Python dependencies
├── run_linux.sh          # Linux startup script
└── run_windows.bat       # Windows startup script
```

## Installation & Running

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Quick Start

#### Linux

```bash
bash run_linux.sh
```

This script will:
1. Create a virtual environment (`.venv`)
2. Install dependencies from `requirements.txt`
3. Start the FastAPI backend on port 8000
4. Launch the Streamlit frontend on port 8501

#### Windows

```batch
run_windows.bat
```

### Manual Installation

If you prefer to set up manually:

```bash
# Create and activate virtual environment
python -m venv .venv

# Activate on Linux/Mac
source .venv/bin/activate

# Activate on Windows
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the backend
uvicorn app.api.main:app --host 127.0.0.1 --port 8000

# In another terminal, start the frontend
streamlit run app/frontend/Home.py
```

## Accessing the Application

Once running, access the application at:

- **Streamlit Frontend**: http://127.0.0.1:8501
- **FastAPI Documentation**: http://127.0.0.1:8000/docs

## Features

### 1. Annual Planning (Planification Annuelle)
Generate complete annual teaching plans for all three middle school levels (1AC, 2AC, 3AC).

### 2. Unit Planning (Planification d'Unité)
Create detailed unit plans with learning objectives and activities.

### 3. Sequence Preparation (Préparation de Séquence)
Prepare individual teaching sequences within units.

### 4. Academic Calendar (Calendrier)
View the official academic calendar with important dates and holidays.

### 5. Settings (Paramètres)
Configure application settings and preferences.

### 6. AI Assistant (Assistant IA)
Get AI-powered answers to pedagogical questions specific to ICT teaching.

### 7. Annual Template (Modèle Annuel)
Access and customize annual planning templates.

## Data Files

The application uses JSON files for data storage:

- **Curriculum Data**: Official ICT curriculum for Moroccan middle schools
- **Calendar Data**: Academic calendar with terms, holidays, and events
- **Pedagogical Framework**: Teaching guidelines and best practices
- **Generated Plans**: User-created annual, unit, and sequence plans

## Dependencies

Key Python packages:
- `fastapi` - Modern web framework for building APIs
- `uvicorn` - ASGI server for running FastAPI
- `streamlit` - Web application framework for ML/AI apps
- `requests` - HTTP library for API calls

## Development

### Adding New Features

1. **Backend**: Add new routes in `app/api/routers_*.py`
2. **Frontend**: Create new pages in `app/frontend/pages/`
3. **Data**: Update JSON files in the `data/` directory

### Scripts

The `scripts/` directory contains utility scripts for:
- Building AI models and datasets
- Cleaning and processing reference data
- Evaluating assistant performance

## Offline-First Design

Collegue AI is designed to work without internet connectivity:
- All data stored locally in JSON files
- No external API dependencies for core features
- AI models run locally when available

## License

[Add license information here]

## Contact

[Add contact information here]
