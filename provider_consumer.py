from __future__ import annotations

# Sample by IoTUeli – https://iotueli.com | LinkedIn: iotueli

import argparse
import asyncio
import datetime as dt
import pathlib
import sys
from typing import Iterable

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
    VARIABLE_DEFINITIONS,
)


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Einfacher Consumer für Temperatur/Diagnosewerte"
    )
    parser.add_argument(
        "--provider",
        default=PROVIDER_ID,
        help="Provider-ID (Standard aus config.py)",
    )
    parser.add_argument(
        "--key",
        action="append",
        help="Variable-Key aus config.py (mehrfach möglich)",
    )
    parser.add_argument(
        "--id",
        type=int,
        action="append",
        help="Variable-ID (mehrfach möglich)",
    )
    parser.add_argument(
        "--default-temperature",
        action="store_true",
        help="Wenn keine IDs angegeben sind, automatisch diagnostics.temperature abonnieren",
    )
    return parser.parse_args()


def _resolve_target_ids(args) -> set[int]:
    targets: set[int] = set(args.id or [])
    if args.key:
        by_key = {var.key: var.id for var in VARIABLE_DEFINITIONS}
        for key in args.key:
            if key not in by_key:
                raise SystemExit(f"Key '{key}' nicht in config.VARIABLE_DEFINITIONS gefunden.")
            targets.add(by_key[key])
    if not targets:
        if args.default_temperature or not (args.id or args.key):
            temp = next(
                (var.id for var in VARIABLE_DEFINITIONS if var.key.endswith("temperature")),
                None,
            )
            if temp is None:
                raise SystemExit(
                    "Keine Temperaturvariable in config.VARIABLE_DEFINITIONS gefunden. "
                    "Bitte --id oder --key angeben."
                )
            targets.add(temp)
    return targets


def _build_runtime(provider_id: str) -> ConsumerRuntime:
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
        variables=[],
    )


def _format_timestamp(ns: int) -> str:
    if not ns:
        return "-"
    return dt.datetime.fromtimestamp(ns / 1_000_000_000).isoformat()


def _print_states(states: Iterable, label: str) -> None:
    print(label)
    for state in states:
        timestamp = _format_timestamp(state.timestamp_ns)
        print(f"  ID {state.id:<4} {state.value!r:>10} @ {timestamp}")


async def main() -> None:
    args = _parse_args()
    target_ids = _resolve_target_ids(args)
    runtime = _build_runtime(args.provider)
    consumer = ConsumerApp(runtime)

    def on_change(states):
        filtered = [s for s in states if s.id in target_ids]
        if filtered:
            _print_states(filtered, "Änderung erhalten:")

    consumer.on_change(on_change)

    await consumer.start()
    try:
        try:
            snapshot = await consumer.request_snapshot()
        except NoRespondersError:
            print(
                f"Kein Provider antwortet auf '{args.provider}'. Läuft der Provider "
                "oder stimmt die ID?"
            )
            return
        filtered_snapshot = [s for s in snapshot if s.id in target_ids]
        if not filtered_snapshot:
            print("Keine der angeforderten Variablen im Snapshot gefunden.")
        else:
            _print_states(filtered_snapshot, "Initiale Werte:")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Beenden...")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())
