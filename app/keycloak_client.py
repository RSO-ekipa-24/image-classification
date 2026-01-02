from keycloak import KeycloakOpenID
import httpx
import time

class KeycloakClient:
    def __init__(self, server_url, realm, client_id, client_secret):
        self.openid = KeycloakOpenID(
            server_url=server_url,
            realm_name=realm,
            client_id=client_id,
            client_secret_key=client_secret
        )
        self._token = None
        self._token_expires_at = 0

    async def get_token(self):
        # Refresh token if expired (with a 30s buffer)
        if not self._token or time.time() > self._token_expires_at - 30:
            token_response = self.openid.token(grant_type="client_credentials")
            self._token = token_response["access_token"]
            self._token_expires_at = time.time() + token_response["expires_in"]
        return self._token

    async def call_other_service(self, url, data):
        token = await self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            if data is None:
                response = await client.get(url, headers=headers)
            else:
                response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()