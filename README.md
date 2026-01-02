# Image Classification Service

A FastAPI service that classifies images stored in Google Cloud Storage using OpenAI's CLIP model. The service fetches available tags from file service and returns tags that fit the image.

## Prerequisites

- Docker & Docker Compose
- Google Cloud Project with Storage API enabled
- Keycloak server configured
- Service account with GCS read permissions

## Google Cloud Setup

### 1. Create a Service Account (if missing)

```bash
# Create service account
gcloud iam service-accounts create image-classifier \
    --display-name="Image Classification Service" \
    --project=$PROJECT_ID

# Grant Storage Object Viewer role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:image-classifier@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"
```

### 2. Configure Service Account Impersonation

```bash
# Authenticate with your user account
gcloud auth application-default login --impersonate-service-account=image-classifier@$PROJECT_ID.iam.gserviceaccount.com

# Verify credentials are set 
# Mac/Linux
ls ~/.config/gcloud/application_default_credentials.json

# Windows
dir %APPDATA%\gcloud\application_default_credentials.json

```

**Note**: The Docker container mounts `~/.config/gcloud` to access these credentials.

## Environment Variables

Create a `.env` file based on `.env.example`:

## Running the Service

### Using Docker Compose

```bash
# Build and start
docker-compose build
docker-compose up

# Stop
docker-compose down
```

The service will be available at `http://localhost:8081`

Service pre-downloads the CLIP model during Docker build to avoid runtime delays. To update the model, rebuild the container:

```bash
docker-compose build --no-cache
```

#### Build and push the image to Google Registry:


First, you need to commit and push all the changes u made to Git!

Then extract your commit hash:

```bash
GIT_HASH=$(git rev-parse --short HEAD)
```
and `echo` it and confirm it matches the hash on GitHub UI.


1Build the local docker image and tag it for Google registry - we will tag it with the commit hash for easier rollbacks and to keep track.

```bash
docker build -f Dockerfile -t europe-central2-docker.pkg.dev/artful-reactor-351917/essa-images/image-classification-service:$GIT_HASH .
```

3. Push to the cloud:

```bash
docker push europe-central2-docker.pkg.dev/artful-reactor-351917/essa-images/image-classification-service:$GIT_HASH
```

