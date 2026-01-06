import os
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError

KEYCLOAK_URL = os.environ["KEYCLOAK_URL"]
REALM = os.environ["KEYCLOAK_REALM_NAME"]
ISSUER = f"{KEYCLOAK_URL}/realms/{REALM}"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"

#EXPECTED_AUDIENCE = "quarkus" #os.getenv("KEYCLOAK_AUDIENCE")  # optional

security = HTTPBearer()
_jwks_cache = None


async def get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(JWKS_URL)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        jwks = await get_jwks()

        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            issuer=ISSUER,
            #audience=EXPECTED_AUDIENCE,
            options={"verify_aud": False},
        )

        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )
    
def require_roles(user: dict, allowed_roles: list[str]):
    roles = user.get("realm_access", {}).get("roles", [])
    if not any(role in roles for role in allowed_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden",)