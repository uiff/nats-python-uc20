from __future__ import annotations

# Sample by IoTUeli – https://iotueli.com | LinkedIn: iotueli

import argparse
import asyncio
import pathlib
import sys

SRC_PATH = pathlib.Path(__file__).resolve().parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from nats.errors import NoRespondersError

from iotueli_sample.auth import OAuthCredentials
from iotueli_sample.models import ConnectionSettings, VariableDefinitionModel
from iotueli_sample.consumer_app import ConsumerApp, ConsumerRuntime
from iotueli_sample.config import (
    CLIENT_ID,
    CLIENT_NAME,
    CLIENT_SECRET,
    HOST,
    PORT,
    PROVIDER_ID,
    TOKEN_ENDPOINT,
)

VARIABLES: list[VariableDefinitionModel] = []


def parse_args():
    parser = argparse.ArgumentParser(description="u-OS Data Hub Consumer")
    parser.add_argument(
        "--provider",
        default=PROVIDER_ID,
        help="Provider-ID, die abgefragt werden soll (Default aus config.py)",
    )
    return parser.parse_args()


def build_runtime(provider_id: str) -> ConsumerRuntime:
    return ConsumerRuntime(
        settings=ConnectionSettings(
            host=HOST,
            port=PORT,
            provider_id=provider_id,
            client_name=CLIENT_NAME,
        ),
        oauth=OAuthCredentials(
            client_name=CLIENT_NAME,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_endpoint=TOKEN_ENDPOINT,
            scope="hub.variables.readwrite",
        ),
        variables=VARIABLES,
    )


async def main() -> None:
    args = parse_args()
    runtime = build_runtime(args.provider)
    consumer = ConsumerApp(runtime)

    def on_change(states):
        print("Änderung erhalten:")
        for state in states:
            print(f"  ID {state.id}: {state.value}")

    consumer.on_change(on_change)

    await consumer.start()
    try:
        try:
            snapshot = await consumer.request_snapshot()
        except NoRespondersError:
            provider_id = runtime.settings.provider_id
            print(
                f"Kein Provider antwortet auf '{provider_id}'. Läuft der Provider "
                "oder ist die Provider-ID korrekt?"
            )
            return
        print("Initiale Werte:")
        for state in snapshot:
            print(f"  ID {state.id}: {state.value}")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Beenden...")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())
