# Deployment Guide

Deploy DecodeNYC to Google Cloud Run with Vertex AI and WebSocket support.

## Prerequisites

- GCP project with billing enabled
- `gcloud` CLI authenticated: `gcloud auth login && gcloud config set project YOUR_PROJECT_ID`
- Docker installed (for local testing)

## Quick Deploy

### One-Time Setup

Enable APIs and create service account:

```bash
cd algorithm-explained

# Enable APIs
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com

# Create service account
export PROJECT_ID=$(gcloud config get-value project)
export SA_NAME=algorithm-explained-sa

gcloud iam service-accounts create $SA_NAME \
  --display-name="Algorithm Explained SA"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Grant Cloud Build permissions
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

**Time:** 2-3 minutes

### Deploy

```bash
cd algorithm-explained
gcloud builds submit --config cloudbuild.yaml
```

**Time:** 3-5 minutes

### Verify

```bash
# Get service URL
export SERVICE_URL=$(gcloud run services describe algorithm-explained \
  --region=us-central1 \
  --format="value(status.url)")

# Test health
curl $SERVICE_URL/health

# Open in browser
open $SERVICE_URL
```

Expected:
- Health returns `{"ok":true}`
- Browser shows interface
- Text and voice modes work

## Configuration

### Service Settings

| Setting | Value | Notes |
|---------|-------|-------|
| Region | us-central1 | Closest to Gemini API |
| Memory | 2Gi | Increase to 4Gi if OOM |
| CPU | 2 vCPU | Handles audio processing |
| Timeout | 3600s | Long WebSocket sessions |
| Min instances | 0 | Set to 1 for production ($15/mo) |
| Max instances | 10 | Increase for high traffic |
| Auth | allow-unauthenticated | Public access |

### Environment Variables

Auto-configured by Cloud Build:

| Variable | Value |
|----------|-------|
| `GOOGLE_GENAI_USE_VERTEXAI` | TRUE |
| `GOOGLE_CLOUD_PROJECT` | $PROJECT_ID |
| `GOOGLE_CLOUD_LOCATION` | us-central1 |
| `DEMO_AGENT_MODEL` | gemini-2.5-flash-native-audio |
| `DATASET_URL` | https://data.cityofnewyork.us/resource/jaw4-yuem.json |
| `PORT` | 8080 (set by Cloud Run) |

### Update Configuration

Change settings without rebuilding:

```bash
# Increase memory
gcloud run services update algorithm-explained \
  --region=us-central1 \
  --memory=4Gi

# Set min instances
gcloud run services update algorithm-explained \
  --region=us-central1 \
  --min-instances=1

# Update env var
gcloud run services update algorithm-explained \
  --region=us-central1 \
  --update-env-vars=DEMO_AGENT_MODEL=new-model-name
```

## Local Testing

Test Docker image before deploying:

```bash
cd algorithm-explained

# Build
docker build -t algorithm-explained:local .

# Run
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY=your_api_key \
  -e GOOGLE_GENAI_USE_VERTEXAI=FALSE \
  algorithm-explained:local

# Test
curl http://localhost:8080/health
open http://localhost:8080
```

## Monitoring

### Cloud Console

View metrics at:
```
https://console.cloud.google.com/run/detail/us-central1/algorithm-explained
```

**Key metrics:**
- Request count and latency (P50, P95, P99)
- Error rate (target: <1%)
- Instance count (autoscaling behavior)
- Memory utilization (keep under 80%)

### Logs

```bash
# Recent logs
gcloud run services logs read algorithm-explained \
  --region=us-central1 \
  --limit=50

# Errors only
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=algorithm-explained \
  AND severity>=ERROR" --limit=20
```

## Troubleshooting

### Cold Start Latency

**Problem:** First request after idle takes 10-30s

**Solution:**
```bash
gcloud run services update algorithm-explained \
  --region=us-central1 \
  --min-instances=1
```

Cost: ~$15/month for always-on instance

### WebSocket Disconnects

**Check timeout is set:**
```bash
gcloud run services describe algorithm-explained \
  --region=us-central1 \
  --format="value(spec.template.spec.timeoutSeconds)"
```

Should be `3600`. If not, redeploy with correct cloudbuild.yaml.

### Vertex AI Auth Errors

**Verify service account:**
```bash
gcloud iam service-accounts list | grep algorithm-explained-sa

gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:algorithm-explained-sa@*" \
  --format="table(bindings.role)"
```

Should show `roles/aiplatform.user`.

### Memory Issues

**Increase allocation:**
```bash
gcloud run services update algorithm-explained \
  --region=us-central1 \
  --memory=4Gi
```

Monitor memory usage in Cloud Console before increasing.

### Dataset API Failures

**Check NYC Open Data status:** https://status.data.cityofnewyork.us/

**Add caching** if rate limits are hit. See [REFERENCE.md](REFERENCE.md) for implementation.

## Updates

### Deploy New Code

```bash
cd algorithm-explained
gcloud builds submit --config cloudbuild.yaml
```

Creates new revision and switches traffic automatically.

### Rollback

```bash
# List revisions
gcloud run revisions list \
  --service=algorithm-explained \
  --region=us-central1

# Rollback
gcloud run services update-traffic algorithm-explained \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100
```

## CI/CD (Optional)

Auto-deploy on git push:

```bash
gcloud builds triggers create github \
  --name=algorithm-explained-deploy \
  --repo-name=YOUR_REPO \
  --repo-owner=YOUR_ORG \
  --branch-pattern=^main$ \
  --build-config=algorithm-explained/cloudbuild.yaml
```

Requires GitHub repo connection via Cloud Console.

## Cost Estimation

**Demo** (0 min instances, 100 sessions/day, 5 min avg):
- Cloud Run compute: $5-10
- Networking: $1
- Container Registry: $0.50
- Vertex AI: $10-20
- **Total: $20-35/month**

**Production** (1 min instance):
- Fixed baseline: $15-20
- Variable compute: $10-15
- Vertex AI: $20-30
- **Total: $50-70/month**

Monitor at: https://console.cloud.google.com/billing

## Security

- Use dedicated service account with minimal permissions
- Never commit API keys or credentials
- Consider `--ingress=internal` if behind load balancer
- Enable Cloud Audit Logs for compliance

## Production Checklist

Before going live:
- [ ] Set min instances based on traffic
- [ ] Configure monitoring alerts
- [ ] Complete load testing (100+ concurrent WebSocket connections)
- [ ] Document incident response procedures
