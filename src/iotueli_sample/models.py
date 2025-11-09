from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VariableType(str, Enum):
    INT64 = "int64"
    FLOAT64 = "float64"
    STRING = "string"
    BOOLEAN = "boolean"


class VariableAccess(str, Enum):
    READ_ONLY = "read-only"
    READ_WRITE = "read-write"


@dataclass
class VariableDefinitionModel:
    id: int
    key: str
    data_type: VariableType
    access: VariableAccess
    experimental: bool = False


@dataclass
class VariableStateModel:
    id: int
    value: Any
    quality: str = "GOOD"
    timestamp_ns: int = field(default=0)


@dataclass
class ConnectionSettings:
    host: str
    port: int
    provider_id: str
    client_name: str
