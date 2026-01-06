import os
import logging
import httpx
from PIL import Image
from io import BytesIO
from fastapi import FastAPI, Depends, HTTPException, Header, Response, status, UploadFile, File
from pydantic import BaseModel
from contextlib import asynccontextmanager

from .classify import classify_image_bytes
from .keycloak_client import KeycloakClient
from .auth import get_current_user, require_roles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Filter health-check logs
logging.getLogger("httpx").setLevel(logging.WARNING)

class EndpointFilter(logging.Filter):
    def filter(self, record):
        return "/health" not in record.getMessage() and "/ready" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

keycloak_client: KeycloakClient | None = None
http_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global keycloak_client, http_client
    
    try:
        http_client = httpx.AsyncClient()
        keycloak_client = KeycloakClient(
            http_client=http_client,
            server_url=os.getenv("KEYCLOAK_URL"),
            realm=os.getenv("KEYCLOAK_REALM_NAME"),
            client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
            client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET"),
        )
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    if http_client:
        await http_client.aclose()
    logger.info("Bye bye!")

app = FastAPI(lifespan=lifespan)

async def download_image_from_url(url: str) -> bytes:
    """Download image from given URL."""
    if not http_client:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        response = await http_client.get(url, timeout=10.0)
        response.raise_for_status()
        return response.content
    
    except httpx.TimeoutException:
        logger.error(f"Timeout downloading image from {url}")
        raise HTTPException(status_code=504, detail="Image download timeout")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading image: {e.response.status_code}")
        raise HTTPException(status_code=502, detail=f"Failed to download image: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Request error downloading image: {e}")
        raise HTTPException(status_code=502, detail="Failed to download image")

async def get_image(uuid: str) -> bytes:
    """Fetch image bytes from file service by UUID."""
    if not http_client:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        url = f"{os.getenv('FILE_SERVICE_URL')}/image/download/{uuid}"
        download_url = await keycloak_client.call_other_service(url, params={"lod": "LOW"})
        return await download_image_from_url(download_url)
    
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching image metadata for {uuid}")
        raise HTTPException(status_code=504, detail="File service timeout")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Image {uuid} not found")
        logger.error(f"File service error: {e.response.status_code}")
        raise HTTPException(status_code=502, detail="File service error")
    except httpx.RequestError as e:
        logger.error(f"File service unreachable: {e}")
        raise HTTPException(status_code=502, detail="File service unavailable")
    
async def get_tags():
    """Fetch tags from file service."""
    if not http_client:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        url = f"{os.getenv('FILE_SERVICE_URL')}/tag/image-system"
        fresh_tags = await keycloak_client.call_other_service(url)

        if "Thumbnail" in fresh_tags: # Part of tags but not useful for classification
            fresh_tags.remove("Thumbnail")

        return fresh_tags
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch tags: {e}")
        return []

async def perfom_classification(image_bytes: bytes):
    """Classify image bytes using available tags."""

    fresh_tags = await get_tags()
    if not fresh_tags or len(fresh_tags) == 0:
        raise HTTPException(status_code=500, detail="No tags available for classification")
    
    try:
        classified_tags = classify_image_bytes(image_bytes, fresh_tags)
        return classified_tags
    except ValueError as e:
        logger.error(f"Invalid image data: {e}")
        raise HTTPException(status_code=400, detail="Invalid image format")
    except Exception as e:
        logger.error(f"Classification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Classification failed")

@app.post("/classify/{uuid}")
async def classify(uuid: str, user=Depends(get_current_user)):
    """Classify an image by UUID."""
    require_roles(user, ["admin", "user"])

    image_bytes = await get_image(uuid)
    results = await perfom_classification(image_bytes)
    return results

@app.post("/classify-file")
async def classify_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Classify an uploaded image file."""
    require_roles(user, ["admin", "user"])

    try:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        image_bytes = await file.read()

        max_size = 10 * 1024 * 1024  # 10MB
        if len(image_bytes) > max_size:
            raise HTTPException(status_code=413, detail="Image too large (max 10MB)")
            
        # Validate image format
        try:
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            image.verify()
        except Exception as e:
            logger.warning(f"Uploaded file is not a valid image: {e}")
            raise HTTPException(status_code=400, detail="File is not a valid image")
            
        results = await perfom_classification(image_bytes)
        return results
    finally:
        await file.close()
        

@app.get("/health", status_code=status.HTTP_200_OK)
async def liveness():
    """Confirms the Python process is running."""
    return {"status": "ok"}

@app.get("/ready")
async def readiness(response: Response):
    """Checks if Keycloak, File Service, and tags are ready."""
    errors = {}

    if not http_client:
        errors["internal"] = "http_client_not_initialized"
    
    if not keycloak_client:
        errors["keycloak"] = "client_not_initialized"

    try:
        fs_url = f"{os.getenv('FILE_SERVICE_URL')}/q/health/ready"
        # keycloak_client also checks connection to keycloak to fetch token
        await keycloak_client.call_other_service(fs_url)
    except Exception as e:
        logger.warning(f"File service health check failed: {e}")
        errors["file_service"] = "unreachable"

    if errors:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "errors": errors}

    return {"status": "ready"}