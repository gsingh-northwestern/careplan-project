# Care Plan Generator

A web application for specialty pharmacies to generate care plans from patient records using AI.

**Live Demo:** https://web-production-a90a.up.railway.app

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

5. **CRITICAL: Check Custom Start Command**
   - Go to: Service → Settings → Deploy → Custom Start Command
   - **Must be EMPTY** (uses Procfile) or contain full command with timeouts
   - If set without timeouts, care plan generation will fail!

6. **Deploy**
   Railway automatically deploys on push to main branch.

### Critical Deployment Note

Care plan generation takes 60-90 seconds. If deployment fails with timeouts:

1. **Custom Start Command**: Must be EMPTY or include `--timeout 300`
2. **Anthropic client**: Must have `timeout=300.0` (already configured)
3. **Procfile**: Must have full timeout settings (already configured)

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

For this prototype, the following were not implemented:

1. **User Authentication**: Would add Django auth for production
2. **Audit Logging**: Would add django-auditlog for PHI compliance
3. **PDF Parsing**: Text input only; would add PyMuPDF for PDF upload
4. **ICD-10 Autocomplete**: Would integrate CMS database
5. **Provider NPI Validation**: Would use NPPES API to verify NPIs

## If I Had Another Day

1. Implement PDF upload with text extraction
2. Add ICD-10 code autocomplete from official database
3. Build dashboard with metrics (orders/day, avg generation time)
4. Add comprehensive test coverage (target 80%)
5. Implement proper logging with structured JSON
6. Add caching for repeated LLM calls

## License

Technical Interview Project for Lamar Health
