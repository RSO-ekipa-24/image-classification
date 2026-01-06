# Image Classification Service

A FastAPI service that classifies images stored in Google Cloud Storage using OpenAI's CLIP model. The service fetches available tags from file service and returns tags that fit the image.

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

