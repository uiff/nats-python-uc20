from __future__ import annotations

import math
import random
import time
from typing import Dict, Iterable

from .models import VariableDefinitionModel, VariableStateModel, VariableType


class SimulationEngine:
    """Erzeugt Dummywerte für unsere Beispielvariablen."""

    def __init__(self, definitions: Iterable[VariableDefinitionModel]) -> None:
        self._definitions = list(definitions)
        self._states: Dict[int, VariableStateModel] = {
            definition.id: VariableStateModel(id=definition.id, value=self._initial_value(definition))
            for definition in self._definitions
        }
        self._tick = 0

    def _initial_value(self, definition: VariableDefinitionModel):
        if definition.data_type == VariableType.INT64:
            return 0
        if definition.data_type == VariableType.FLOAT64:
            return 0.0
        if definition.data_type == VariableType.STRING:
            if definition.key.endswith("static_message"):
                return "Hello from IoTUeli"
            return "ready"
        if definition.data_type == VariableType.BOOLEAN:
            return False
        return 0

    def advance(self) -> list[VariableStateModel]:
        self._tick += 1
        now_ns = int(time.time() * 1_000_000_000)

        for definition in self._definitions:
            state = self._states[definition.id]
            state.timestamp_ns = now_ns

            if definition.data_type == VariableType.INT64:
                state.value = int(state.value) + 1
            elif definition.data_type == VariableType.FLOAT64:
                state.value = round(20.0 + math.sin(self._tick / 5.0) * 5.0, 3)
            elif definition.data_type == VariableType.STRING:
                if definition.key.endswith("static_message"):
                    state.value = "Hello from IoTUeli"
                else:
                    state.value = random.choice(["ready", "running", "idle"])
            elif definition.data_type == VariableType.BOOLEAN:
                state.value = not bool(state.value)

        return list(self._states.values())

    @property
    def states(self) -> list[VariableStateModel]:
        return list(self._states.values())
