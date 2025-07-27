#!/bin/bash
set -e

# Deployment script for Google Cloud
PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}

echo "🚀 Deploying The Assistant to Google Cloud"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "📡 Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com

# Create secrets (you'll need to add the actual values)
echo "🔐 Creating secrets..."
echo "Please set the following secrets manually:"
echo "gcloud secrets create db-encryption-key --data-file=<(echo 'your-32-char-key')"
echo "gcloud secrets create jwt-secret --data-file=<(echo 'your-jwt-secret')"
echo "gcloud secrets create telegram-token --data-file=<(echo 'your-telegram-token')"

# Build and deploy using Cloud Build
echo "🏗️ Building and deploying with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml

echo "✅ Deployment complete!"
echo "Check your Cloud Run services:"
echo "gcloud run services list --region=$REGION"