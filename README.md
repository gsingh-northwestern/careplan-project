# Care Plan Generator

A web application for specialty pharmacies to generate care plans from patient records using AI.

**Live Demo:** [https://web-production-baa93.up.railway.app/orders/new/](https://web-production-baa93.up.railway.app/orders/new/)

**Design & User Journey:** [Figma Board](https://www.figma.com/board/9XyF0eifxW45fTG60LJs69/Lamar-Health---Care-Plan-Project?node-id=2-16&t=h71BJT3G39KtgUQh-1)

## Problem Statement

Specialty pharmacies spend 20-40 minutes per patient manually creating care plans. These care plans are required for:
- Medicare compliance
- Pharma reimbursement

This tool automates the process using AI while ensuring data integrity through validation and duplicate detection.

## Features

- **Patient & Provider Management**: Create and manage patient and provider records
- **Input Validation**: Strict validation for NPI (10 digits), MRN (6 digits), ICD-10 codes
- **Duplicate Detection**:
  - Blocks exact duplicates (same NPI, same MRN)
  - Warns on potential duplicates (similar names, same patient + medication)
- **AI Care Plan Generation**: Uses Claude API to generate comprehensive care plans
- **Export**: CSV export for pharma reporting

## Tech Stack

- **Backend**: Django 5.x
- **Frontend**: Django Templates + HTMX + Tailwind CSS
- **Database**: SQLite (development) / PostgreSQL (production)
- **AI**: Anthropic Claude API
- **Hosting**: Railway

## Quick Start (Local Development)

### Prerequisites

- Python 3.10+
- pip

### Installation

1. **Clone and enter directory**
   ```bash
   cd lamar-careplan
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY (optional)
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

7. **Open in browser**
   ```
   http://localhost:8000
   ```

## Deployment (Railway)

The application is configured for one-click deployment to Railway.

> **See [DEPLOYMENT.md](DEPLOYMENT.md)** for detailed deployment guide with troubleshooting.

### Deploy to Railway

1. **Push to GitHub** (if not already)
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/gsingh-northwestern/careplan-project.git
   git push -u origin main
   ```

2. **Connect to Railway**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

3. **Add PostgreSQL**
   - In Railway dashboard, click "New" → "Database" → "PostgreSQL"
   - Railway automatically sets `DATABASE_URL`

4. **Configure Environment Variables**
   In Railway dashboard → Variables, add:
   ```
   DJANGO_SECRET_KEY=<generate-a-secure-key>
   DEBUG=False
   LLM_MOCK_MODE=False
   ANTHROPIC_API_KEY=<your-api-key>
   ```

5. **CRITICAL: Set Custom Start Command**
   - Go to: Service → Settings → Deploy → Custom Start Command
   - **Set this exact command** (runs migrations + starts server with timeouts):
     ```
     python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 300 --worker-class gthread --workers 1 --threads 4
     ```
   - If left empty, migrations won't run (Railway ignores Procfile `release` commands)

6. **Deploy**
   Railway automatically deploys on push to main branch.

### Critical Deployment Notes

1. **Custom Start Command is REQUIRED** - Railway ignores Procfile `release` commands, so migrations must be in the start command
2. **Timeouts**: Care plan generation takes 60-90 seconds. The start command includes `--timeout 300` for gunicorn, and `llm_service.py` has `timeout=300.0` for the Anthropic client

See [DEPLOYMENT.md](DEPLOYMENT.md) for full troubleshooting guide.

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DJANGO_SECRET_KEY` | Django secret key | Yes (production) |
| `DEBUG` | Debug mode | No (default: True) |
| `ANTHROPIC_API_KEY` | Claude API key | For AI generation |
| `LLM_MOCK_MODE` | Use mock AI responses | No (default: True) |
| `DATABASE_URL` | PostgreSQL connection | Auto-set by Railway |

## Configuration

### Mock Mode

By default, the app runs in mock mode (`LLM_MOCK_MODE=True`), which generates sample care plans without calling the Claude API. This is useful for testing.

To use real AI generation:
1. Get an API key from https://console.anthropic.com/
2. Set `ANTHROPIC_API_KEY` in environment variables
3. Set `LLM_MOCK_MODE=False`

## Running Tests

```bash
python manage.py test tests
```

## Project Structure

```
lamar-careplan/
├── config/                 # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── careplan/              # Main application
│   ├── models.py          # Data models
│   ├── validators.py      # Input validation
│   ├── duplicates.py      # Duplicate detection
│   ├── llm_service.py     # Claude API integration
│   ├── views.py           # Request handlers
│   ├── forms.py           # Django forms
│   └── urls.py            # URL routing
├── templates/             # HTML templates
├── tests/                 # Unit tests
├── Procfile               # Railway/Heroku process file
├── runtime.txt            # Python version
├── requirements.txt
└── README.md
```

## Data Models

### Provider
- `name`: Provider full name
- `npi`: National Provider Identifier (10 digits, unique)

### Patient
- `first_name`, `last_name`: Patient name
- `mrn`: Medical Record Number (6 digits, unique)
- `dob`: Date of birth (required)

### Order
- Links patient and provider
- Contains diagnosis codes, medication, and patient records
- Status: draft → submitted → completed

### CarePlan
- Generated content from AI
- Metadata: model used, generation time

## Validation Rules

| Field | Rule |
|-------|------|
| NPI | Exactly 10 digits |
| MRN | Exactly 6 digits |
| ICD-10 | Format: A00 or A00.0000 |
| DOB | Not in future, age 0-120 |

## Duplicate Detection

### Provider Duplicates
- **Block**: Same NPI already exists
- **Warn**: Similar name with different NPI

### Patient Duplicates
- **Block**: Same MRN already exists
- **Warn**: Same name + DOB with different MRN

### Order Duplicates
- **Warn (HIGH)**: Same patient + medication on the SAME DAY
- **Warn (MEDIUM)**: Same patient + medication within 30 days

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Redirect to order creation |
| `/orders/` | GET | List all orders |
| `/orders/new/` | GET/POST | Create new order |
| `/orders/<id>/` | GET | View order details |
| `/orders/<id>/generate/` | POST | Generate care plan |
| `/orders/<id>/download/` | GET | Download care plan as text |
| `/export/csv/` | GET | Export all orders to CSV |

## What's Intentionally Left Out

**Philosophy:** Build and validate core platform and data models first, enabling easier demo and iteration before adding complexity.

| Feature | Reason | Production Path |
|---------|--------|-----------------|
| **User Authentication** | Prioritized core workflow demo | Django auth with role-based permissions |
| **Audit Logging** | Adds complexity for initial demo | django-auditlog for HIPAA PHI access tracking |
| **PDF Parsing** | User research showed copy/paste from EHR is dominant workflow | PyMuPDF or pdfplumber for PDF upload |
| **ICD-10 Autocomplete** | Would require external database integration | CMS ICD-10 database with typeahead search |
| **NPI Validation** | External API dependency | NPPES API for real-time verification |

## If I Had Another Day

### High Priority
- **PHI Tokenization** - Replace identifiers with tokens before LLM calls (critical for HIPAA without BAA)
- **Async Generation** - Background task queue (Celery) for care plan generation with progress indicator
- **Response Streaming** - Stream care plan as it generates for better UX

### Medium Priority
- **LLM Agnostic Architecture** - Abstract provider interface to swap between Claude/GPT/Llama
- **Caching Layer** - Redis cache for repeated LLM calls with similar inputs

### Lower Priority
- **Analytics Dashboard** - Orders/day, avg generation time, model usage metrics
- **Structured JSON Logging** - Machine-parseable logs for aggregation

## License

Technical Interview Project for Lamar Health
