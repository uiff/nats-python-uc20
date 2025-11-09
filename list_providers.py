from __future__ import annotations

# Sample by IoTUeli – https://iotueli.com | LinkedIn: iotueli

import asyncio
import pathlib
import sys
from typing import Iterable

SRC_PATH = pathlib.Path(__file__).resolve().parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from iotueli_sample.auth import OAuthCredentials, request_token
from iotueli_sample.config import (
    CLIENT_ID,
    CLIENT_NAME,
    CLIENT_SECRET,
    HOST,
    PORT,
    TOKEN_ENDPOINT,
)
from iotueli_sample.nats_client import NatsConnection
from iotueli_sample.payloads import build_read_providers_query
from iotueli_sample.subjects import (
    registry_providers_changed_event,
    registry_providers_query,
)
from weidmueller.ucontrol.hub.ProvidersChangedEvent import ProvidersChangedEvent
from weidmueller.ucontrol.hub.ReadProvidersQueryResponse import (
    ReadProvidersQueryResponse,
)
from weidmueller.ucontrol.hub.ProviderList import ProviderList

def _decode_provider_ids(provider_list: ProviderList | None) -> list[str]:
    if provider_list is None or provider_list.ItemsIsNone():
        return []
    provider_ids: list[str] = []
    for idx in range(provider_list.ItemsLength()):
        item = provider_list.Items(idx)
        if item is None:
            continue
        provider_id = item.Id()
        if provider_id is None:
            continue
        if isinstance(provider_id, (bytes, bytearray)):
            provider_id = provider_id.decode("utf-8")
        provider_ids.append(str(provider_id))
    return provider_ids


def _print_providers(provider_ids: Iterable[str], prefix: str) -> None:
    ids = sorted(provider_ids)
    if not ids:
        print(f"{prefix}: <keine Provider gefunden>")
        return
    print(prefix + ":")
    for pid in ids:
        print(f"  - {pid}")


async def _fetch_current_providers(conn: NatsConnection) -> list[str]:
    payload = build_read_providers_query()
    msg = await conn.request(registry_providers_query(), payload, timeout=2.0)
    response = ReadProvidersQueryResponse.GetRootAsReadProvidersQueryResponse(
        msg.data, 0
    )
    return _decode_provider_ids(response.Providers())


async def main() -> None:
    oauth = OAuthCredentials(
        client_name=CLIENT_NAME,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_endpoint=TOKEN_ENDPOINT,
        scope="hub.variables.readwrite",
    )
    token = await request_token(oauth)

    conn = NatsConnection(
        host=HOST,
        port=PORT,
        client_name=f"{CLIENT_NAME}-registry-listener",
        token=token,
    )
    await conn.connect()

    async def on_update(msg):
        event = ProvidersChangedEvent.GetRootAsProvidersChangedEvent(msg.data, 0)
        provider_ids = _decode_provider_ids(event.Providers())
        _print_providers(provider_ids, "Update vom Registry")

    await conn.subscribe(registry_providers_changed_event(), callback=on_update)

    snapshot = await _fetch_current_providers(conn)
    _print_providers(snapshot, "Aktuelle Provider")
    print("Warte auf weitere Provider-Events (Strg+C zum Beenden)...")

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("Beenden...")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
