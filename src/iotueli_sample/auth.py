from __future__ import annotations

import httpx
from dataclasses import dataclass


@dataclass
class OAuthCredentials:
    client_name: str
    client_id: str
    client_secret: str
    token_endpoint: str
    scope: str


async def request_token(credentials: OAuthCredentials) -> str:
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            credentials.token_endpoint,
            headers={"Accept": "application/json"},
            auth=(credentials.client_id, credentials.client_secret),
            data={
                "grant_type": "client_credentials",
                "scope": credentials.scope,
            },
            timeout=10.0,
        )

    response.raise_for_status()
    data = response.json()
    token = data.get("access_token")
    if not token:
        raise ValueError(f"Antwort enthielt kein access_token: {data}")
    return token
