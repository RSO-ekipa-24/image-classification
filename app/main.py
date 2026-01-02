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
    """Confirms the app has its tags and can reach Keycloak."""
    is_ready = True
    details = {}

    # Check 1: Were tags successfully loaded into the global variable?
    if not tags:
        is_ready = False
        details["tags"] = "not_loaded"

    # Check 2: Is Keycloak reachable?
    try:
        async with httpx.AsyncClient() as client:
            # We ping the Keycloak URL defined in your env
            res = await client.get(os.getenv("KEYCLOAK_URL"), timeout=1.0)
            if res.status_code >= 400:
                is_ready = False
                details["keycloak"] = f"unreachable_status_{res.status_code}"
    except Exception as e:
        is_ready = False
        details["keycloak"] = str(e)

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "details": details}

    return {"status": "ready", "tags_count": len(tags)}