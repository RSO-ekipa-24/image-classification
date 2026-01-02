from fastapi import FastAPI, Depends, HTTPException
from keycloak_auth.keycloak_auth import KeycloakAuth, Header
from pydantic import BaseModel
from contextlib import asynccontextmanager
from .gcs import download_image
from .classify import classify_image_bytes
from .keycloak_client import KeycloakClient
import os
import logging
from fastapi import Response, status
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tags = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tags
    logger.info("=== APPLICATION STARTUP ===")
    # Startup - fetch tags
    client = KeycloakClient(
        server_url=os.getenv("KEYCLOAK_URL"),
        realm=os.getenv("KEYCLOAK_REALM_NAME"),
        client_id=os.getenv("KEYCLOAK_SERVICE_CLIENT_ID"),
        client_secret=os.getenv("KEYCLOAK_SERVICE_CLIENT_SECRET"),
    )
    tags = await client.call_other_service(os.getenv("FILE_SERVICE_TAGS_URL"), None)
    logger.info(f"TAGS LOADED: {tags}")
    logger.info(f"Number of tags: {len(tags)}")
    yield
    # Shutdown
    logger.info("=== APPLICATION SHUTDOWN ===")

app = FastAPI(lifespan=lifespan)

auth = KeycloakAuth()

class ImageRequest(BaseModel):
    bucket: str
    object_path: str

@app.post("/classify")
@auth.RolesAllowed(['admin', 'user'])
async def classify(
    request: ImageRequest,
    authorization: str | None = Header(default=None)
):
    # This code only runs if the token is valid
    img_bytes = download_image(request.bucket, request.object_path)
    tags = classify_image_bytes(img_bytes)
    return {"object": request.object_path, "tags": tags, "classified_by": user.preferred_username}



@app.get("/health", status_code=status.HTTP_200_OK)
async def liveness():
    """Confirms the Python process is running."""
    return {"status": "ok"}

@app.get("/ready")
async def readiness(response: Response):
    """Checks if Keycloak, the File Service, and internal tags are all ready."""
    errors = {}

    async with httpx.AsyncClient() as client:
        # 1. Check Keycloak
        try:
            kc_res = await client.get(os.getenv("KEYCLOAK_URL"), timeout=1.0)
            if kc_res.status_code >= 400:
                errors["keycloak"] = f"unhealthy_status_{kc_res.status_code}"
        except Exception:
            errors["keycloak"] = "unreachable"

        # 2. Check File Service health
        try:
            fs_base = "http://files-service:8080"
            fs_res = await client.get(f"{fs_base}/q/health/ready", timeout=1.0)
            if fs_res.status_code != 200:
                errors["file_service"] = f"unhealthy_{fs_res.status_code}"
        except Exception:
            errors["file_service"] = "unreachable"

    # 3. Check if we actually have tags in memory
    if not tags:
        errors["internal_state"] = "tags_list_empty"

    if errors:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "errors": errors}

    return {"status": "ready", "tags_loaded": len(tags)}