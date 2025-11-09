from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, List

from nats.aio.msg import Msg

from weidmueller.ucontrol.hub.VariablesChangedEvent import VariablesChangedEvent
from weidmueller.ucontrol.hub.ReadVariablesQueryResponse import ReadVariablesQueryResponse
from weidmueller.ucontrol.hub.VariableValue import VariableValue
from weidmueller.ucontrol.hub.VariableValueBoolean import VariableValueBoolean
from weidmueller.ucontrol.hub.VariableValueFloat64 import VariableValueFloat64
from weidmueller.ucontrol.hub.VariableValueInt64 import VariableValueInt64
from weidmueller.ucontrol.hub.VariableValueString import VariableValueString

from .auth import OAuthCredentials, request_token
from .models import ConnectionSettings, VariableDefinitionModel, VariableStateModel
from .nats_client import NatsConnection
from .payloads import build_read_variables_query
from .subjects import read_variables_query, vars_changed_event


@dataclass
class ConsumerRuntime:
    settings: ConnectionSettings
    oauth: OAuthCredentials
    variables: List[VariableDefinitionModel]


class ConsumerApp:
    def __init__(self, runtime: ConsumerRuntime) -> None:
        self.runtime = runtime
        self._nats: NatsConnection | None = None
        self._callbacks: list[Callable[[list[VariableStateModel]], None]] = []
        self._states: dict[int, VariableStateModel] = {}

    def on_change(self, cb: Callable[[list[VariableStateModel]], None]) -> None:
        self._callbacks.append(cb)

    async def start(self) -> None:
        token = await request_token(self.runtime.oauth)
        self._nats = NatsConnection(
            host=self.runtime.settings.host,
            port=self.runtime.settings.port,
            client_name=self.runtime.settings.client_name,
            token=token,
        )
        await self._nats.connect()
        await self._nats.subscribe(
            vars_changed_event(self.runtime.settings.provider_id),
            callback=self._handle_event,
        )

    async def stop(self) -> None:
        if self._nats:
            await self._nats.close()
            self._nats = None

    async def request_snapshot(self) -> list[VariableStateModel]:
        if not self._nats:
            raise RuntimeError("Consumer ist nicht gestartet")
        payload = build_read_variables_query(None)
        msg = await self._nats.request(
            read_variables_query(self.runtime.settings.provider_id),
            payload,
            timeout=2.0,
        )
        response = ReadVariablesQueryResponse.GetRootAsReadVariablesQueryResponse(msg.data, 0)
        return self._update_states(response.Variables())

    async def _handle_event(self, msg: Msg) -> None:
        event = VariablesChangedEvent.GetRootAsVariablesChangedEvent(msg.data, 0)
        changed = self._update_states(event.ChangedVariables())
        if not changed:
            return
        for cb in self._callbacks:
            cb(changed)

    def _update_states(self, var_list) -> list[VariableStateModel]:
        if not var_list:
            return []

        base_ts = var_list.BaseTimestamp()
        base_ns = base_ts.Seconds() * 1_000_000_000 + base_ts.Nanos()

        changed: list[VariableStateModel] = []

        for i in range(var_list.ItemsLength()):
            item = var_list.Items(i)
            if item is None:
                continue
            var_id = item.Id()

            state = self._states.setdefault(var_id, VariableStateModel(id=var_id, value=None))
            state.timestamp_ns = base_ns

            value_type = item.ValueType()
            value_table = item.Value()

            if value_table is None:
                continue

            if value_type == VariableValue.Int64:
                holder = VariableValueInt64()
                holder.Init(value_table.Bytes, value_table.Pos)
                state.value = holder.Value()
            elif value_type == VariableValue.Float64:
                holder = VariableValueFloat64()
                holder.Init(value_table.Bytes, value_table.Pos)
                state.value = holder.Value()
            elif value_type == VariableValue.String:
                holder = VariableValueString()
                holder.Init(value_table.Bytes, value_table.Pos)
                state.value = holder.Value().decode("utf-8")
            elif value_type == VariableValue.Boolean:
                holder = VariableValueBoolean()
                holder.Init(value_table.Bytes, value_table.Pos)
                state.value = bool(holder.Value())

            changed.append(state)

        return changed
