from keycloak import KeycloakOpenID
import httpx
import time

class KeycloakClient:
    def __init__(self, http_client, server_url, realm, client_id, client_secret):
        self.http_client = http_client
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

    async def call_other_service(self, url, params=None, data=None, timeout=5.0):
        token = await self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        if data is None:
            response = await self.http_client.get(url, params=params, headers=headers, timeout=timeout)
        else:
            response = await self.http_client.post(url, params=params, json=data, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()