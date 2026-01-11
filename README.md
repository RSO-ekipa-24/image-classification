# Image Classification Service  

## Overview
A FastAPI service that classifies images stored in Google Cloud Storage using OpenAI's CLIP model. The service fetches available tags from file service and returns tags that fit the image.


### Branching Strategy

- main: The production-ready branch.
- dev: The integration branch for features and fixes, often considered the "next release" branch.
- feature/: Branches for developing new features. These branches are created from dev and merged back into dev when the feature is complete.
- bugfix/: Branches for fixing bugs in the dev branch.
- release/: Branches for preparing a new production release. These branches allow for last-minute fixes and preparing release notes.
- hotfix/: Branches for fixing critical issues in the main branch. These are created from main and merged back into both main and dev.

### Technology stack :computer:

| Category                  | Technology / Tool |
|----------------------------|-------------------|
| Backend framework          | Python (FastAPI)  |
| Containerization           | Docker            |
| CI/CD Automation           | GitHub Actions    |

---

## Prerequisites

- Docker & Docker Compose
- Keycloak server configured
- File service deployed

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

## Build and push the image to Google Registry:


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

### Deploy via helm chart :arrow_up:

Move to `image-classification/deploy/k8s/helm` and run:

```bash
helm upgrade --install image-classification-release ./image-classification --set deployment.image.tag=$GIT_HASH
```
