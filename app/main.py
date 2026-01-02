from fastapi import FastAPI, Depends, HTTPException
from keycloak_auth.keycloak_auth import KeycloakAuth, Header
from pydantic import BaseModel
from contextlib import asynccontextmanager
from .gcs import download_image
from .classify import classify_image_bytes
from .keycloak_client import KeycloakClient
import os
import logging

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