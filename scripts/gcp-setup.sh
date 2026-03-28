#!/bin/bash
# Cloud Run Setup Script
# Run this once to configure GCP resources for algorithm-explained deployment

set -e

echo "=== DecodeNYC - GCP Setup ==="
echo ""

# Get project ID
export PROJECT_ID=$(gcloud config get-value project)
echo "Project ID: $PROJECT_ID"
echo ""

# Step 1: Enable APIs
echo "Step 1/4: Enabling GCP APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable aiplatform.googleapis.com
echo "✓ APIs enabled"
echo ""

# Step 2: Create Service Account
echo "Step 2/4: Creating service account..."
export SA_NAME=algorithm-explained-sa

gcloud iam service-accounts create $SA_NAME \
  --display-name="Algorithm Explained Cloud Run SA" \
  --quiet || echo "Service account already exists"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user" \
  --quiet

echo "✓ Service account created: $SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
echo ""

# Step 3: Configure Cloud Build Permissions
echo "Step 3/4: Configuring Cloud Build permissions..."
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin" \
  --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser" \
  --quiet

echo "✓ Cloud Build permissions configured"
echo ""

# Step 4: Optional - Create Cloud Build Trigger
echo "Step 4/4: Cloud Build Trigger (optional)"
echo "To set up automated deployment on git push, run:"
echo ""
echo "  gcloud builds triggers create github \\"
echo "    --name=algorithm-explained-deploy \\"
echo "    --repo-name=YOUR_REPO_NAME \\"
echo "    --repo-owner=YOUR_GITHUB_ORG \\"
echo "    --branch-pattern=^main$ \\"
echo "    --build-config=algorithm-explained/cloudbuild.yaml \\"
echo "    --included-files=algorithm-explained/**"
echo ""
echo "Replace YOUR_REPO_NAME and YOUR_GITHUB_ORG with actual values."
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Ready to deploy! Run:"
echo "  cd algorithm-explained"
echo "  gcloud builds submit --config cloudbuild.yaml"
echo ""
