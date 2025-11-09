from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List

from weidmueller.ucontrol.hub import WriteVariablesCommand
from weidmueller.ucontrol.hub import ProviderDefinitionChangedEvent
from weidmueller.ucontrol.hub.Variable import Variable
from weidmueller.ucontrol.hub.VariableValue import VariableValue
from weidmueller.ucontrol.hub.VariableValueBoolean import (
    VariableValueBoolean,
)
from weidmueller.ucontrol.hub.VariableValueFloat64 import (
    VariableValueFloat64,
)
from weidmueller.ucontrol.hub.VariableValueInt64 import (
    VariableValueInt64,
)
from weidmueller.ucontrol.hub.VariableValueString import (
    VariableValueString,
)

from .auth import OAuthCredentials, request_token
from .models import ConnectionSettings, VariableDefinitionModel, VariableStateModel, VariableType
from .nats_client import NatsConnection
from .payloads import (
    build_provider_definition_event,
    build_read_variables_query,
    build_read_variables_response,
    build_variables_changed_event,
)
from .simulation import SimulationEngine
from .subjects import (
    provider_changed_event,
    read_variables_query,
    registry_provider_event,
    vars_changed_event,
    write_variables_command,
)


@dataclass
class ProviderRuntime:
    settings: ConnectionSettings
    variables: List[VariableDefinitionModel]
    oauth: OAuthCredentials
    publish_interval: float = 1.0


class ProviderApp:
    def __init__(self, runtime: ProviderRuntime) -> None:
        self.runtime = runtime
        self._nats: NatsConnection | None = None
        self._sim = SimulationEngine(runtime.variables)
        self._tasks: list[asyncio.Task] = []
        self._fingerprint: int = 0

    async def start(self) -> None:
        token = await request_token(self.runtime.oauth)
        self._nats = NatsConnection(
            host=self.runtime.settings.host,
            port=self.runtime.settings.port,
            client_name=self.runtime.settings.client_name,
            token=token,
        )
        await self._nats.connect()
        print("NATS-Verbindung steht")

        await self._nats.subscribe(
            registry_provider_event(self.runtime.settings.provider_id),
            callback=self._handle_registry_update,
        )
        print("Registrierungs-Subscription eingerichtet")

        await self._register_provider_definition()
        print(
            f"Providerdefinition publiziert auf {provider_changed_event(self.runtime.settings.provider_id)}"
        )

        await self._nats.subscribe(
            read_variables_query(self.runtime.settings.provider_id),
            callback=self._handle_read_request,
        )
        print("Read-Subscription aktiv")
        await self._nats.subscribe(
            write_variables_command(self.runtime.settings.provider_id),
            callback=self._handle_write_command,
        )
        print("Write-Subscription aktiv")

        self._tasks.append(asyncio.create_task(self._publish_loop()))
        print("Publish-Loop gestartet")

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self._nats:
            await self._nats.close()
            self._nats = None

    async def _register_provider_definition(self) -> None:
        payload, fingerprint = build_provider_definition_event(self.runtime.variables)
        self._fingerprint = fingerprint
        await self._nats.publish(
            provider_changed_event(self.runtime.settings.provider_id), payload
        )

    async def _handle_read_request(self, msg) -> None:
        states = self._sim.states
        payload = build_read_variables_response(self.runtime.variables, states, self._fingerprint)
        await self._nats.publish(msg.reply, payload)

    async def _handle_write_command(self, msg) -> None:
        command = WriteVariablesCommand.WriteVariablesCommand.GetRootAsWriteVariablesCommand(
            msg.data, 0
        )
        var_list = command.Variables()
        if not var_list:
            return

        for i in range(var_list.ItemsLength()):
            item = var_list.Items(i)
            if not item:
                continue
            var_id = item.Id()
            state = next((s for s in self._sim.states if s.id == var_id), None)
            if state is None:
                continue

            value_type = item.ValueType()
            if value_type == VariableValue.Int64:
                holder = VariableValueInt64()
                item.Value(holder)
                state.value = holder.Value()
            elif value_type == VariableValue.Float64:
                holder = VariableValueFloat64()
                item.Value(holder)
                state.value = holder.Value()
            elif value_type == VariableValue.String:
                holder = VariableValueString()
                item.Value(holder)
                state.value = holder.Value().decode("utf-8")
            elif value_type == VariableValue.Boolean:
                holder = VariableValueBoolean()
                item.Value(holder)
                state.value = bool(holder.Value())

        await self._publish_once()

    async def _publish_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.runtime.publish_interval)
                self._sim.advance()
                await self._publish_once()
        except asyncio.CancelledError:
            pass

    async def _publish_once(self) -> None:
        states = self._sim.states
        payload = build_variables_changed_event(self.runtime.variables, states, self._fingerprint)
        await self._nats.publish(
            vars_changed_event(self.runtime.settings.provider_id), payload
        )

    async def _handle_registry_update(self, msg) -> None:
        event = ProviderDefinitionChangedEvent.GetRootAsProviderDefinitionChangedEvent(
            msg.data, 0
        )
        definition = event.ProviderDefinition()
        if not definition:
            print("Registry meldet Provider entfernt")
            return
        state = definition.State()
        status = {0: "UNSPECIFIED", 1: "OK", 2: "INVALID"}.get(state, str(state))
        print(f"Registry-Status für Provider: {status}")


def build_connection_settings(host: str, port: int, provider_id: str, client_name: str) -> ConnectionSettings:
    return ConnectionSettings(host=host, port=port, provider_id=provider_id, client_name=client_name)
