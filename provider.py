from __future__ import annotations

# Sample by IoTUeli – https://iotueli.com | LinkedIn: iotueli

import asyncio
import pathlib
import sys

SRC_PATH = pathlib.Path(__file__).resolve().parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from iotueli_sample.auth import OAuthCredentials
from iotueli_sample.models import ConnectionSettings
from iotueli_sample.provider_app import ProviderApp, ProviderRuntime
from iotueli_sample.config import (
    CLIENT_ID,
    CLIENT_NAME,
    CLIENT_SECRET,
    HOST,
    PORT,
    PROVIDER_ID,
    TOKEN_ENDPOINT,
    PUBLISH_INTERVAL_SECONDS,
    VARIABLE_DEFINITIONS,
)


def build_runtime() -> ProviderRuntime:
    return ProviderRuntime(
        settings=ConnectionSettings(
            host=HOST,
            port=PORT,
            provider_id=PROVIDER_ID,
            client_name=CLIENT_NAME,
        ),
        publish_interval=PUBLISH_INTERVAL_SECONDS,
        variables=VARIABLE_DEFINITIONS,
        oauth=OAuthCredentials(
            client_name=CLIENT_NAME,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_endpoint=TOKEN_ENDPOINT,
            scope="hub.variables.provide hub.variables.readwrite",
        ),
    )


async def main() -> None:
    runtime = build_runtime()
    provider = ProviderApp(runtime)
    await provider.start()
    print("Provider gestartet – Strg+C zum Beenden.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Beenden...")
    finally:
        await provider.stop()


if __name__ == "__main__":
    asyncio.run(main())
