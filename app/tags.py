import httpx
import os

async def fetch_tags_from_file_service():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(os.getenv("FILE_SERVICE_TAGS_URL"))
            response.raise_for_status()
            tags = response.json()  # Expecting a list like ["kitchen", "bedroom", ...]
            return tags if tags else None
    except Exception as e:
        print(f"Failed to fetch tags: {e}")
        return None