# Lamar Health Interview - Whiteboard Prep

## Interview Phases & What to Expect

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INTERVIEW TIMELINE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 1: Eesha Call (Now)                                              │
│  ─────────────────────────                                              │
│  • Clarify requirements                                                  │
│  • Understand user (Medical Assistant) workflow                          │
│  • Align on P0/P1/P2 priorities                                         │
│  • Ask questions that show product thinking                              │
│  Duration: 30 min?                                                       │
│                                                                          │
│  PHASE 2: Build Period (T=0 to T+?)                                     │
│  ─────────────────────────────────                                      │
│  • Build the prototype                                                   │
│  • We already have this done!                                           │
│  • Use this time to polish based on Eesha's feedback                    │
│  Duration: ??? (ask Eesha)                                              │
│                                                                          │
│  PHASE 3: Technical Review                                               │
│  ─────────────────────────                                              │
│  • Demo the working product                                              │
│  • Walk through code architecture                                        │
│  • Discuss trade-offs and decisions                                      │
│  • Answer technical questions                                            │
│  Duration: ???                                                           │
│                                                                          │
│  PHASE 4: Final Interview                                                │
│  ────────────────────────                                               │
│  • Product/design discussion?                                            │
│  • Team fit?                                                             │
│  Duration: ???                                                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Questions About the Process (Ask Eesha)
- [ ] How much time do I have for the build phase?
- [ ] What does the technical review look like? Live demo? Code walkthrough?
- [ ] Will there be follow-up interviews after the technical review?
- [ ] Should I deploy it somewhere, or run locally during review?

---

## Questions to Ask Eesha

### Understanding the User
| # | Question | Notes |
|---|----------|-------|
| 1 | "Walk me through a typical day for the medical assistant. What's the current process?" | |
| 2 | "What's most frustrating about the current care plan creation process?" | |
| 3 | "How tech-comfortable are the MAs? Power users or need simple UI?" | |
| 4 | "How long does it currently take to create one care plan?" | |

### Understanding the Workflow
| # | Question | Notes |
|---|----------|-------|
| 5 | "One order = one medication, or can an order have multiple meds?" | |
| 6 | "Do MAs always have the provider NPI, or do they need to look it up?" | |
| 7 | "Will patient records always be text, or do we need PDF/image upload?" | |
| 8 | "Who reviews the generated care plans before they're finalized?" | |

### Understanding Duplicates
| # | Question | Notes |
|---|----------|-------|
| 9 | "How often do duplicates actually happen? 1%? 10%?" | |
| 10 | "When a duplicate is detected, should it block or just warn?" | |
| 11 | "What should happen if they confirm it's NOT a duplicate?" | |

### Understanding Success
| # | Question | Notes |
|---|----------|-------|
| 12 | "How is success measured? Time saved? Error reduction?" | |
| 13 | "What's the failure mode if a care plan is wrong?" | |
| 14 | "What specific fields do pharma companies need in exports?" | |

### Scoping the Prototype
| # | Question | Notes |
|---|----------|-------|
| 15 | "What's the ONE feature that would make the biggest impact?" | |
| 16 | "What absolutely cannot be missing from the prototype?" | |
| 17 | "What would be nice-to-have but not essential?" | |

---

## Feature Ranking Exercise

**Instructions:** Review this list with Eesha. Mark each as P0 (must have), P1 (should have), or P2 (nice to have).

### Core Data Entry
| Feature | My Guess | Eesha's Priority | Notes |
|---------|----------|------------------|-------|
| Provider name + NPI input | P0 | | |
| Patient name + MRN input | P0 | | |
| Date of birth field | P1 | | |
| Primary diagnosis (ICD-10) | P0 | | |
| Additional diagnoses | P1 | | |
| Medication name | P0 | | |
| Medication history | P1 | | |
| Patient records text field | P0 | | |

### Validation
| Feature | My Guess | Eesha's Priority | Notes |
|---------|----------|------------------|-------|
| NPI format validation (10 digits) | P0 | | |
| MRN format validation (6 digits) | P0 | | |
| ICD-10 format validation | P1 | | |
| DOB validation (not future) | P2 | | |
| Required field validation | P0 | | |

### Duplicate Detection
| Feature | My Guess | Eesha's Priority | Notes |
|---------|----------|------------------|-------|
| Block duplicate NPI | P0 | | |
| Warn similar provider name | P1 | | |
| Block duplicate MRN | P0 | | |
| Warn same name+DOB, different MRN | P1 | | |
| Warn same patient+medication (30 days) | P1 | | |

### AI Generation
| Feature | My Guess | Eesha's Priority | Notes |
|---------|----------|------------------|-------|
| Generate care plan from records | P0 | | |
| Structured output (sections) | P1 | | |
| Regenerate option | P2 | | |
| Edit generated plan | P2 | | |

### Data Management
| Feature | My Guess | Eesha's Priority | Notes |
|---------|----------|------------------|-------|
| View list of orders | P1 | | |
| View order details | P1 | | |
| Download care plan (text) | P1 | | |
| CSV export for pharma | P1 | | |

### NOT Building (Confirm with Eesha)
| Feature | Reason | Eesha Agrees? |
|---------|--------|---------------|
| User authentication | Prototype scope | |
| PDF upload/parsing | Scope creep | |
| ICD-10 autocomplete | Would need CMS database | |
| NPI verification (NPPES API) | External dependency | |
| Audit logging | Production concern | |

---

## My Technical Approach (To Share if Asked)

```
Stack:
├── Django 5.x (backend)
├── HTMX (interactivity without JS complexity)
├── Tailwind CSS (clean, professional UI)
├── Claude API (care plan generation)
├── PostgreSQL (production) / SQLite (dev)
└── Railway (deployment)

Why this stack:
• Django - required by job posting, great for rapid prototyping
• HTMX - real-time validation without SPA complexity
• Tailwind - fast styling, professional healthcare look
• Claude - best for medical content, long context window
```

---

## Notes During Call

### Key Insights
```
_________________________________________________________________

_________________________________________________________________

_________________________________________________________________

_________________________________________________________________

_________________________________________________________________
```

### Priority Changes
```
What moved UP in priority:
_________________________________________________________________

What moved DOWN in priority:
_________________________________________________________________

Surprises:
_________________________________________________________________
```

### Action Items After Call
```
[ ] _______________________________________________________________

[ ] _______________________________________________________________

[ ] _______________________________________________________________

[ ] _______________________________________________________________
```

---

## Quick Reference: What We've Built

| Component | Status | Notes |
|-----------|--------|-------|
| Django project structure | ✅ Done | |
| Data models (Provider, Patient, Order, CarePlan) | ✅ Done | |
| Order creation form | ✅ Done | |
| NPI/MRN/ICD-10 validation | ✅ Done | |
| Duplicate detection (all 3 types) | ✅ Done | |
| HTMX real-time warnings | ✅ Done | |
| Claude API integration | ✅ Done | Mock + Real mode |
| Care plan generation | ✅ Done | |
| Order list view | ✅ Done | |
| Order detail view | ✅ Done | |
| CSV export | ✅ Done | |
| Download care plan | ✅ Done | |
| Unit tests (46) | ✅ Done | All passing |
| Railway deployment config | ✅ Done | Ready to deploy |
| Clean UI (Linear/Notion style) | ✅ Done | |

**Live demo ready at:** `http://localhost:8000` (local)
**Will deploy to:** `https://lamar-careplan.up.railway.app`

---

## Deployment Lessons Learned (CRITICAL)

### The Three Issues We Encountered

1. **Railway Custom Start Command Overrides Procfile**
   - If Custom Start Command is set in Railway UI, it COMPLETELY IGNORES Procfile
   - Fix: Leave Custom Start Command EMPTY or copy full command with timeouts

2. **Anthropic SDK Default 30-Second Timeout**
   - httpx (used by anthropic SDK) has 30s default
   - Care plans take 60-90 seconds
   - Fix: `client = anthropic.Anthropic(api_key=key, timeout=300.0)`

3. **Gunicorn Worker Configuration**
   - Default sync workers get killed on long requests
   - Fix: Use `--timeout 300 --graceful-timeout 300 --worker-class gthread`

### Quick Deployment Checklist

- [ ] Push to GitHub
- [ ] Create Railway project from repo
- [ ] Add PostgreSQL database
- [ ] Set environment variables:
  - `DJANGO_SECRET_KEY`
  - `DEBUG=False`
  - `LLM_MOCK_MODE=False`
  - `ANTHROPIC_API_KEY`
- [ ] **CHECK Custom Start Command is EMPTY** (Settings → Deploy)
- [ ] Verify deployment works

### Working Configuration

**Model**: `claude-sonnet-4-5-20250929`

**Procfile**:
```
web: gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 300 --worker-class gthread --workers 1 --threads 4
release: python manage.py migrate --noinput
```

**Railway Custom Start Command**: EMPTY (or copy Procfile web command)

### If Care Plan Generation Fails

1. Check Railway logs for "Starting API call" message
2. If it appears but no completion → timeout issue
3. Go to Settings → Deploy → Custom Start Command
4. Make sure it's EMPTY or has full timeout settings
