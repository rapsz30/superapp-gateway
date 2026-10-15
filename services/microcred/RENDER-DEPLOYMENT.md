# Render Deployment Guide

## Quick Start Deployment to Render

### Step 1: Push Your Code to GitHub
```bash
# Make sure all changes are committed
git add -A
git commit -m "feat: add Render deployment configuration"
git push origin main
```

### Step 2: Create Render Account
1. Go to [https://render.com](https://render.com)
2. Sign up with GitHub account
3. Authorize Render to access your repositories

### Step 3: Deploy Using Blueprint
1. Click **"New +"** → **"Blueprint"**
2. Select your **MicroCred-genAI** repository
3. Render will detect `render.yaml` automatically
4. Click **"Apply"**

Render will create:
- ✅ **Web Service** (microcred-api) - FastAPI application
- ✅ **PostgreSQL Database** (microcred-db) - PostgreSQL 16
- ✅ **Redis Instance** (microcred-redis) - Redis cache

### Step 4: Set Environment Variables
After blueprint is applied, go to **microcred-api** service:

1. **Environment** tab
2. Add **OPENAI_API_KEY**:
   - Key: `OPENAI_API_KEY`
   - Value: `sk-your-openai-api-key`
3. Click **"Save Changes"**

The service will automatically redeploy.

### Step 5: Verify Deployment
```bash
# Wait for deployment to complete (~3-5 minutes)
# Check your service URL (e.g., https://microcred-api.onrender.com)

# Test health endpoint
curl https://microcred-api.onrender.com/health

# Expected response:
# {"status":"ok","timestamp":"2025-12-30T10:00:00Z"}
```

### Step 6: Access API Documentation
```
https://microcred-api.onrender.com/docs      # Swagger UI
https://microcred-api.onrender.com/redoc     # ReDoc
```

---

## Manual Deployment (Alternative)

If you prefer manual setup instead of Blueprint:

### 1. Create PostgreSQL Database
1. Dashboard → **"New +"** → **"PostgreSQL"**
2. Name: `microcred-db`
3. Database Name: `microcred`
4. Region: Singapore (or closest to you)
5. Plan: **Starter** (Free for 90 days)
6. Click **"Create Database"**
7. Copy **Internal Database URL** from Info tab

### 2. Create Redis Instance
1. Dashboard → **"New +"** → **"Redis"**
2. Name: `microcred-redis`
3. Region: Singapore (same as database)
4. Plan: **Starter** (Free)
5. Click **"Create Redis"**
6. Copy **Internal Redis URL** from Info tab

### 3. Create Web Service
1. Dashboard → **"New +"** → **"Web Service"**
2. Connect your repository
3. Configure:
   - **Name**: `microcred-api`
   - **Region**: Singapore
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `./scripts/render-build.sh`
   - **Start Command**: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Starter (Free)

4. **Environment Variables** (click "Advanced"):
   ```
   PYTHON_VERSION=3.12.2
   POETRY_VERSION=1.8.4
   DATABASE_URL=<paste-postgres-internal-url>
   REDIS_URL=<paste-redis-internal-url>
   OPENAI_API_KEY=sk-your-key
   JWT_SECRET_KEY=<generate-random-32-chars>
   JWT_ALGORITHM=HS256
   ENVIRONMENT=production
   LOG_LEVEL=info
   ```

5. Click **"Create Web Service"**

---

## Configuration Details

### render.yaml Explained
```yaml
services:
  - type: web
    name: microcred-api
    buildCommand: ./scripts/render-build.sh  # Installs deps + runs migrations
    startCommand: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase: microcred-db  # Auto-linked
      - key: REDIS_URL
        fromService: microcred-redis  # Auto-linked
```

### Build Process (render-build.sh)
1. Install Poetry
2. Install Python dependencies (production only)
3. Run database migrations (`alembic upgrade head`)
4. Ready to serve traffic

---

## Pricing (As of 2025)

### Free Tier Includes:
- ✅ **Web Service**: 750 hours/month (1 instance)
- ✅ **PostgreSQL**: Free for 90 days, then $7/month
- ✅ **Redis**: 25 MB storage, persistent
- ⚠️ **Limitation**: Services spin down after 15 min inactivity (cold start ~30s)

### Paid Plans:
- **Starter**: $7/month (always on, no cold starts)
- **Standard**: $25/month (more resources)
- **Pro**: Custom pricing

---

## Post-Deployment Checklist

### ✅ Verify Services Running
```bash
# Health check
curl https://your-app.onrender.com/health

# List tracks
curl https://your-app.onrender.com/tracks

# API docs
open https://your-app.onrender.com/docs
```

### ✅ Test Assessment Flow
```bash
# Generate token (run locally with your JWT secret)
TOKEN=$(python -c "from src.core.auth import create_access_token; print(create_access_token('test', roles=['student']))")

# Start assessment
curl -X POST https://your-app.onrender.com/assessments/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role_slug": "backend-engineer"}'
```

### ✅ Monitor Logs
1. Go to service dashboard
2. Click **"Logs"** tab
3. Watch for errors or warnings

### ✅ Setup Custom Domain (Optional)
1. Service Settings → **"Custom Domain"**
2. Add your domain: `api.yourdomain.com`
3. Update DNS with provided CNAME record
4. SSL certificate auto-provisioned

---

## Troubleshooting

### Issue: Build Failed - Poetry Not Found
**Solution**: Check `POETRY_VERSION` env var matches installed version
```bash
# In render-build.sh, ensure:
pip install poetry==1.8.4
```

### Issue: Database Connection Error
**Solution**: Verify DATABASE_URL is set correctly
```bash
# In Render dashboard:
# Environment → DATABASE_URL should start with postgresql://
```

### Issue: Migration Failed
**Solution**: Check migration files are committed to git
```bash
git add alembic/versions/*.py
git commit -m "add migrations"
git push
```

### Issue: Cold Start Too Slow
**Solution**: Upgrade to Starter plan ($7/month) for always-on instance

### Issue: OpenAI API Key Not Set
**Solution**: Add manually in Environment tab
```
Key: OPENAI_API_KEY
Value: sk-your-actual-key
```

---

## Continuous Deployment

Render auto-deploys on every git push to main:

```bash
# Make changes locally
git add .
git commit -m "feat: new feature"
git push origin main

# Render automatically:
# 1. Detects push
# 2. Runs build script
# 3. Runs migrations
# 4. Deploys new version
# 5. Zero-downtime deployment
```

---

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `REDIS_URL` | ✅ | Redis connection string | `redis://host:6379/0` |
| `OPENAI_API_KEY` | ✅ | OpenAI API key | `sk-...` |
| `JWT_SECRET_KEY` | ✅ | JWT signing secret (32+ chars) | Auto-generated or custom |
| `JWT_ALGORITHM` | ✅ | JWT algorithm | `HS256` |
| `ENVIRONMENT` | ⚠️ | Environment name | `production` |
| `LOG_LEVEL` | ⚠️ | Logging level | `info` or `warning` |
| `PORT` | 🔄 | HTTP port (auto-set by Render) | `10000` |

---

## Scaling Strategies

### Horizontal Scaling
```yaml
# In render.yaml, add:
services:
  - type: web
    scaling:
      minInstances: 2
      maxInstances: 5
      targetMemoryPercent: 80
      targetCPUPercent: 80
```

### Database Scaling
- Upgrade PostgreSQL plan in dashboard
- Consider connection pooling (PgBouncer)

### Caching
- Redis already included
- Implement caching in FastAPI routes

---

## Backup & Recovery

### Database Backups
Render automatically backs up PostgreSQL:
- **Frequency**: Daily
- **Retention**: 7 days (Starter), 30 days (Standard+)

### Manual Backup
```bash
# Download backup
render db:download microcred-db ./backup.sql

# Restore backup
render db:restore microcred-db ./backup.sql
```

---

## Security Best Practices

### ✅ Secrets Management
- Never commit API keys to git
- Use Render environment variables
- Rotate JWT secrets regularly

### ✅ HTTPS Everywhere
- Render provides free SSL certificates
- All traffic encrypted by default

### ✅ Database Security
- Use Internal URLs for database connections
- PostgreSQL not exposed to internet
- Automatic security patches

### ✅ CORS Configuration
Update CORS settings for production domain:
```python
# src/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Next Steps After Deployment

1. **Connect Frontend**: Update frontend API URL to Render endpoint
2. **Setup Monitoring**: Add Sentry or DataDog for error tracking
3. **Add Analytics**: Track API usage and performance
4. **Configure Alerts**: Get notified of downtime or errors
5. **Setup CI/CD**: Add GitHub Actions for automated testing before deploy

---

## Support Resources

- **Render Docs**: https://render.com/docs
- **Community Forum**: https://community.render.com
- **Status Page**: https://status.render.com
- **Support**: support@render.com

---

**🎉 Your MicroCred API is now live on Render!**
