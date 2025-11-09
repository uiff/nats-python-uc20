from __future__ import annotations

# Sample by IoTUeli – https://iotueli.com | LinkedIn: iotueli

import argparse
import asyncio
import pathlib
import sys
import time
from typing import Iterable, Optional

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
from iotueli_sample.models import (
    VariableAccess,
    VariableDefinitionModel,
    VariableStateModel,
    VariableType,
)
from iotueli_sample.nats_client import NatsConnection
from iotueli_sample.payloads import (
    build_read_provider_definition_query,
    build_read_providers_query,
    build_read_variables_query,
    build_write_variables_command,
)
from iotueli_sample.subjects import (
    read_variables_query,
    registry_provider_query,
    registry_providers_query,
    write_variables_command,
)
from weidmueller.ucontrol.hub.ReadProvidersQueryResponse import (
    ReadProvidersQueryResponse,
)
from weidmueller.ucontrol.hub.ReadProviderDefinitionQueryResponse import (
    ReadProviderDefinitionQueryResponse,
)
from weidmueller.ucontrol.hub.ReadVariablesQueryResponse import (
    ReadVariablesQueryResponse,
)
from weidmueller.ucontrol.hub.VariableValue import VariableValue
from weidmueller.ucontrol.hub.VariableValueBoolean import VariableValueBoolean
from weidmueller.ucontrol.hub.VariableValueFloat64 import VariableValueFloat64
from weidmueller.ucontrol.hub.VariableValueInt64 import VariableValueInt64
from weidmueller.ucontrol.hub.VariableValueString import VariableValueString
from weidmueller.ucontrol.hub.ProviderDefinitionState import ProviderDefinitionState
from weidmueller.ucontrol.hub.VariableAccessType import VariableAccessType
from weidmueller.ucontrol.hub.VariableDataType import VariableDataType


DATA_TYPE_LABELS = {
    VariableDataType.BOOLEAN: "BOOLEAN",
    VariableDataType.FLOAT64: "FLOAT64",
    VariableDataType.INT64: "INT64",
    VariableDataType.STRING: "STRING",
}

ACCESS_TYPE_LABELS = {
    VariableAccessType.READ_ONLY: "READ_ONLY",
    VariableAccessType.READ_WRITE: "READ_WRITE",
}

DATA_TYPE_TO_MODEL = {
    VariableDataType.BOOLEAN: VariableType.BOOLEAN,
    VariableDataType.FLOAT64: VariableType.FLOAT64,
    VariableDataType.INT64: VariableType.INT64,
    VariableDataType.STRING: VariableType.STRING,
}

ACCESS_TYPE_TO_MODEL = {
    VariableAccessType.READ_ONLY: VariableAccess.READ_ONLY,
    VariableAccessType.READ_WRITE: VariableAccess.READ_WRITE,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Werkzeug zum Lesen/Schreiben von u-OS Provider-Variablen"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-providers", help="Alle registrierten Provider anzeigen")

    describe = sub.add_parser("describe", help="Definition eines Providers anzeigen")
    describe.add_argument("--provider", required=True, help="Provider-ID")

    read = sub.add_parser("read", help="Aktuelle Werte vom Provider anfragen")
    read.add_argument("--provider", required=True, help="Provider-ID")
    read.add_argument("--key", help="Optional nur eine Variable (Key) lesen")
    read.add_argument("--id", type=int, help="Optional nur eine Variable (ID) lesen")

    write = sub.add_parser("write", help="Schreibt einen Wert auf eine Variable")
    write.add_argument("--provider", required=True, help="Provider-ID")
    target = write.add_mutually_exclusive_group(required=True)
    target.add_argument("--key", help="Variable über ihren Key adressieren")
    target.add_argument("--id", type=int, help="Variable über ihre ID adressieren")
    write.add_argument(
        "--value",
        required=True,
        help="Wert, der geschrieben werden soll (als Text, wird konvertiert)",
    )

    return parser.parse_args()


async def open_connection(client_suffix: str) -> NatsConnection:
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
        client_name=f"{CLIENT_NAME}-{client_suffix}",
        token=token,
    )
    await conn.connect()
    return conn


def _decode_provider_list(payload: bytes) -> list[str]:
    response = ReadProvidersQueryResponse.GetRootAsReadProvidersQueryResponse(payload, 0)
    provider_list = response.Providers()
    if provider_list is None:
        return []
    result: list[str] = []
    for idx in range(provider_list.ItemsLength()):
        item = provider_list.Items(idx)
        if item is None:
            continue
        provider_id = item.Id()
        if isinstance(provider_id, (bytes, bytearray)):
            provider_id = provider_id.decode("utf-8")
        result.append(str(provider_id))
    return sorted(result)


async def list_providers(conn: NatsConnection) -> None:
    payload = build_read_providers_query()
    msg = await conn.request(registry_providers_query(), payload, timeout=2.0)
    for pid in _decode_provider_list(msg.data):
        print(f"- {pid}")


def _decode_definition_models(definition) -> tuple[list[VariableDefinitionModel], dict[int, dict]]:
    variables: list[VariableDefinitionModel] = []
    info: dict[int, dict] = {}
    if definition is None or definition.VariableDefinitionsIsNone():
        return variables, info

    for idx in range(definition.VariableDefinitionsLength()):
        entry = definition.VariableDefinitions(idx)
        if entry is None:
            continue
        key = entry.Key()
        if isinstance(key, (bytes, bytearray)):
            key = key.decode("utf-8")
        access_raw = entry.AccessType()
        data_raw = entry.DataType()
        model: Optional[VariableDefinitionModel] = None
        access = ACCESS_TYPE_LABELS.get(access_raw, f"UNKNOWN({access_raw})")
        data_type = DATA_TYPE_LABELS.get(data_raw, f"UNKNOWN({data_raw})")
        if data_raw in DATA_TYPE_TO_MODEL and access_raw in ACCESS_TYPE_TO_MODEL:
            model = VariableDefinitionModel(
                id=entry.Id(),
                key=str(key),
                data_type=DATA_TYPE_TO_MODEL[data_raw],
                access=ACCESS_TYPE_TO_MODEL[access_raw],
                experimental=entry.Experimental(),
            )
            variables.append(model)

        info[entry.Id()] = {
            "id": entry.Id(),
            "key": str(key),
            "access": access,
            "data_type": data_type,
            "experimental": entry.Experimental(),
            "model": model,
        }
    return variables, info


async def fetch_definition(conn: NatsConnection, provider_id: str):
    payload = build_read_provider_definition_query()
    msg = await conn.request(
        registry_provider_query(provider_id), payload, timeout=2.0
    )
    response = ReadProviderDefinitionQueryResponse.GetRootAsReadProviderDefinitionQueryResponse(
        msg.data, 0
    )
    definition = response.ProviderDefinition()
    if definition is None:
        raise RuntimeError(f"Keine Definition für Provider '{provider_id}' gefunden.")
    return definition


def _state_label(state: int) -> str:
    return {
        ProviderDefinitionState.UNSPECIFIED: "UNSPECIFIED",
        ProviderDefinitionState.OK: "OK",
        ProviderDefinitionState.INVALID: "INVALID",
    }.get(state, f"UNKNOWN({state})")


async def describe_provider(conn: NatsConnection, provider_id: str) -> None:
    definition = await fetch_definition(conn, provider_id)
    variables, info = _decode_definition_models(definition)
    print(f"Provider: {provider_id}")
    print(f"Fingerprint: {definition.Fingerprint()}")
    print(f"State: {_state_label(definition.State())}")
    print("Variablen:")
    for entry in sorted(info.values(), key=lambda x: x["id"]):
        print(
            f"  ID {entry['id']:>3}  | {entry['key']:<50} | {entry['data_type']:<10} | {entry['access']}"
            + (" (RW)" if entry["access"] == "READ_WRITE" else "")
        )
    if not info:
        print("  <keine Variablen>")


def _decode_values(var_list, selected: dict[int, dict]) -> list[dict]:
    if not var_list:
        return []
    base_ts = var_list.BaseTimestamp()
    base_ns = base_ts.Seconds() * 1_000_000_000 + base_ts.Nanos()
    rows: list[dict] = []
    for idx in range(var_list.ItemsLength()):
        item = var_list.Items(idx)
        if item is None:
            continue
        value_table = item.Value()
        if value_table is None:
            continue
        value_type = item.ValueType()
        if value_type == VariableValue.Int64:
            holder = VariableValueInt64()
            holder.Init(value_table.Bytes, value_table.Pos)
            value = holder.Value()
        elif value_type == VariableValue.Float64:
            holder = VariableValueFloat64()
            holder.Init(value_table.Bytes, value_table.Pos)
            value = holder.Value()
        elif value_type == VariableValue.String:
            holder = VariableValueString()
            holder.Init(value_table.Bytes, value_table.Pos)
            value = holder.Value().decode("utf-8")
        elif value_type == VariableValue.Boolean:
            holder = VariableValueBoolean()
            holder.Init(value_table.Bytes, value_table.Pos)
            value = bool(holder.Value())
        else:
            value = "<unbekannter Typ>"
        rows.append(
            {
                "id": item.Id(),
                "value": value,
                "timestamp_ns": base_ns,
                "definition": selected.get(item.Id()),
            }
        )
    return rows


async def read_values(
    conn: NatsConnection,
    provider_id: str,
    key: str | None,
    var_id: int | None,
) -> None:
    definition = await fetch_definition(conn, provider_id)
    _, info = _decode_definition_models(definition)

    target_ids: Optional[list[int]] = None
    if key:
        matches = [entry["id"] for entry in info.values() if entry["key"] == key]
        if not matches:
            raise RuntimeError(f"Key '{key}' nicht gefunden.")
        target_ids = matches
    elif var_id is not None:
        if var_id not in info:
            raise RuntimeError(f"Variable-ID {var_id} nicht gefunden.")
        target_ids = [var_id]

    payload = build_read_variables_query(target_ids)
    msg = await conn.request(
        read_variables_query(provider_id),
        payload,
        timeout=2.0,
    )
    response = ReadVariablesQueryResponse.GetRootAsReadVariablesQueryResponse(
        msg.data, 0
    )
    rows = _decode_values(response.Variables(), info)
    if not rows:
        print("Keine Werte erhalten.")
        return
    for row in rows:
        definition_entry = row["definition"]
        if definition_entry:
            key_label = definition_entry["key"]
        else:
            key_label = "<unbekannt>"
        print(f"{key_label} (ID {row['id']}): {row['value']}")


def _convert_value(model: VariableDefinitionModel, value: str):
    if model.data_type == VariableType.INT64:
        return int(value)
    if model.data_type == VariableType.FLOAT64:
        return float(value)
    if model.data_type == VariableType.STRING:
        return value
    if model.data_type == VariableType.BOOLEAN:
        if value.lower() in {"true", "1", "on", "yes"}:
            return True
        if value.lower() in {"false", "0", "off", "no"}:
            return False
        raise ValueError("Boolean-Wert bitte als true/false oder 1/0 angeben.")
    raise ValueError(f"Datentyp {model.data_type} wird für Schreibbefehle nicht unterstützt.")


async def write_value(
    conn: NatsConnection,
    provider_id: str,
    key: str | None,
    var_id: int | None,
    value: str,
) -> None:
    definition = await fetch_definition(conn, provider_id)
    _, info = _decode_definition_models(definition)

    selected: Optional[VariableDefinitionModel] = None
    if key:
        for entry in info.values():
            if entry["key"] == key:
                selected = entry["model"]
                break
        if selected is None:
            raise RuntimeError(f"Key '{key}' nicht gefunden oder nicht unterstützter Typ.")
    elif var_id is not None:
        entry = info.get(var_id)
        if entry:
            selected = entry["model"]
    if selected is None:
        raise RuntimeError("Variable konnte nicht ermittelt werden.")
    if selected.access != VariableAccess.READ_WRITE:
        raise RuntimeError("Variable ist nicht beschreibbar.")

    converted_value = _convert_value(selected, value)
    state = VariableStateModel(
        id=selected.id,
        value=converted_value,
        timestamp_ns=time.time_ns(),
    )
    payload = build_write_variables_command([selected], [state])
    await conn.publish(write_variables_command(provider_id), payload)
    print(
        f"Befehl gesendet: {selected.key} (ID {selected.id}) <- {converted_value!r}"
    )
    # Optional Feedback durch erneutes Lesen
    await asyncio.sleep(0.2)
    await read_values(conn, provider_id, selected.key, None)


async def main_async():
    args = parse_args()
    conn = await open_connection(client_suffix="cli")
    try:
        if args.command == "list-providers":
            await list_providers(conn)
        elif args.command == "describe":
            await describe_provider(conn, args.provider)
        elif args.command == "read":
            await read_values(conn, args.provider, args.key, args.id)
        elif args.command == "write":
            await write_value(conn, args.provider, args.key, args.id, args.value)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main_async())
