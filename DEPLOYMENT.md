# Railway Deployment Guide

**Current Production URL:** https://web-production-baa93.up.railway.app/orders/new/

This guide covers deploying the Care Plan Generator to Railway, including critical lessons learned from debugging production issues.

## Quick Start

### Prerequisites
- GitHub account
- Railway account (railway.app)
- Anthropic API key (console.anthropic.com)

### 5-Minute Deployment

```bash
# 1. Push to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/gsingh-northwestern/careplan-project.git
git push -u origin main
```

Then in Railway:
1. New Project → Deploy from GitHub repo
2. Add PostgreSQL database
3. Set environment variables (see below)
4. **CRITICAL**: Set Custom Start Command (see step 5 below)
5. Deploy

---

## Critical Configuration

### Environment Variables

| Variable | Value | Required |
|----------|-------|----------|
| `DJANGO_SECRET_KEY` | Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` | Yes |
| `DEBUG` | `False` | Yes |
| `LLM_MOCK_MODE` | `False` | Yes (for real AI) |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Yes (for real AI) |
| `DATABASE_URL` | Auto-set by Railway | Auto |

### Procfile (Already Configured)

```
web: gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 300 --worker-class gthread --workers 1 --threads 4
release: python manage.py migrate --noinput
```

---

## Critical Lessons Learned

### Issue #1: Railway Doesn't Auto-Run Procfile `release` Commands

**Problem**: Database tables don't exist after deployment. Migrations never ran.

**Root Cause**: Railway doesn't automatically execute `release:` commands from Procfile like Heroku does. The Procfile `release: python manage.py migrate --noinput` is ignored.

**Fix**: Combine migrations into the start command. Set Custom Start Command to:
```
python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 300 --worker-class gthread --workers 1 --threads 4
```

This ensures migrations run every time the container starts, before gunicorn launches.

---

### Issue #2: Railway Custom Start Command Overrides Procfile

**Problem**: Care plan generation worked locally but failed on Railway with worker timeouts after ~30 seconds.

**Root Cause**: Railway has a "Custom Start Command" setting in Settings → Deploy. If this is set to ANY value, it COMPLETELY IGNORES the Procfile.

**Fix**:
- Go to: Service → Settings → Deploy → Custom Start Command
- Either leave it **EMPTY** (recommended - uses Procfile)
- Or copy the FULL Procfile command into it:
  ```
  gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 300 --worker-class gthread --workers 1 --threads 4
  ```

### Issue #3: Anthropic SDK Default 30-Second Timeout

**Problem**: The `anthropic` Python SDK uses `httpx` under the hood, which has a default 30-second timeout. Care plan generation takes 60-90+ seconds.

**Fix**: Set explicit timeout when creating the client in `llm_service.py`:
```python
client = anthropic.Anthropic(
    api_key=api_key,
    timeout=300.0  # 5 minutes
)
```

### Issue #4: Gunicorn Worker Configuration

**Problem**: Default gunicorn uses sync workers with 30-second timeout. Long-running API requests get killed.

**Fix**: Use these gunicorn settings:
```
--timeout 300           # Worker timeout (5 min)
--graceful-timeout 300  # Graceful shutdown timeout
--worker-class gthread  # Threaded workers for IO-bound ops
--workers 1             # Single worker (Railway free tier)
--threads 4             # 4 threads per worker
```

---

## Debugging Checklist

### If Care Plan Generation Fails

1. **Check Railway Logs**
   - Filter by your app name
   - Look for "Starting API call" message
   - If it appears but no completion → timeout issue

2. **Verify Custom Start Command**
   - Service → Settings → Deploy → Custom Start Command
   - Should be EMPTY or have full timeout settings

3. **Check API Key**
   - Logs should show: `API key configured: prefix=sk-ant-api0..., length=108`
   - If not, check environment variables

4. **Test Locally First**
   ```python
   import anthropic
   client = anthropic.Anthropic(api_key="sk-ant-...")
   response = client.messages.create(
       model="claude-sonnet-4-5-20250929",
       max_tokens=100,
       messages=[{"role": "user", "content": "Say hello"}]
   )
   print(response.content[0].text)
   ```

### Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| `Worker timeout` / `SIGABRT` | Gunicorn killing slow workers | Check Custom Start Command |
| `ReadTimeout` | httpx 30s default | Add `timeout=300.0` to Anthropic client |
| `401 Unauthorized` | Bad API key | Check ANTHROPIC_API_KEY env var |
| `404 Not Found` | Wrong model ID | Use `claude-sonnet-4-5-20250929` |

---

## Step-by-Step Deployment

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/gsingh-northwestern/careplan-project.git
git push -u origin main
```

### 2. Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your repository
5. Select `lamar-careplan`

### 3. Add PostgreSQL Database

1. In Railway dashboard, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway automatically injects `DATABASE_URL`

### 4. Set Environment Variables

Go to your service → Variables tab:

```
DJANGO_SECRET_KEY=<your-generated-key>
DEBUG=False
LLM_MOCK_MODE=False
ANTHROPIC_API_KEY=sk-ant-...
```

### 5. CRITICAL: Set Custom Start Command

1. Go to service → Settings → Deploy
2. Find "Custom Start Command"
3. **Set it to this exact command** (runs migrations then starts server):
   ```
   python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 300 --worker-class gthread --workers 1 --threads 4
   ```
4. If left empty, migrations won't run and you'll get "no such table" errors
5. If set without migrations, database tables won't be created

### 6. Deploy

Railway auto-deploys when you push. You can also:
- Click "Deploy" manually in dashboard
- View logs to monitor progress

### 7. Verify

1. Visit your Railway URL
2. Create a test order
3. Generate a care plan
4. Should complete in ~60-90 seconds

---

## Working Configuration Reference

**Model**: `claude-sonnet-4-5-20250929`

**Procfile**:
```
web: gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 300 --worker-class gthread --workers 1 --threads 4
release: python manage.py migrate --noinput
```

**llm_service.py client**:
```python
client = anthropic.Anthropic(
    api_key=api_key,
    timeout=300.0
)
```

**Railway Custom Start Command** (REQUIRED - do not leave empty):
```
python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 300 --worker-class gthread --workers 1 --threads 4
```

**Success Metrics**:
- Care plan generation: ~60-90 seconds
- No worker timeouts
- Full care plan output

---

## Troubleshooting

### "Application failed to respond" or 502 errors

1. Check Railway logs for errors
2. Verify PostgreSQL is connected
3. Check DATABASE_URL is set

### Care plan generation times out

1. **First**: Check Custom Start Command setting
2. Verify llm_service.py has `timeout=300.0`
3. Check Procfile has full timeout settings

### "Invalid API key" errors

1. Verify ANTHROPIC_API_KEY is set in Railway variables
2. Make sure key starts with `sk-ant-`
3. Check key hasn't been revoked in Anthropic console

### Database migration errors

1. Check `release` command in Procfile
2. Manually run: `python manage.py migrate` locally first
3. Check for syntax errors in models
