#!/bin/bash
# Deploy Algorithm Explained to Cloud Run

set -e

echo "=== Deploying Algorithm Explained to Cloud Run ==="
echo ""

# Get project ID
export PROJECT_ID=$(gcloud config get-value project)
echo "Project ID: $PROJECT_ID"
echo ""

# Check if in correct directory
if [ ! -f "cloudbuild.yaml" ]; then
  echo "Error: Must run from algorithm-explained directory"
  echo "Run: cd algorithm-explained && ./scripts/deploy.sh"
  exit 1
fi

# Submit build
echo "Submitting build to Cloud Build..."
echo "This will take 3-5 minutes..."
echo ""

gcloud builds submit --config cloudbuild.yaml

echo ""
echo "=== Deployment Complete ==="
echo ""

# Get service URL
export SERVICE_URL=$(gcloud run services describe algorithm-explained \
  --region=us-central1 \
  --format="value(status.url)")

echo "Service URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "  1. Test health: curl $SERVICE_URL/health"
echo "  2. Open in browser: open $SERVICE_URL"
echo "  3. View logs: gcloud run services logs read algorithm-explained --region=us-central1"
echo ""
