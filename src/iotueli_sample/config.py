from __future__ import annotations

"""Central place to edit host, credentials, provider ID and variables.

Vor jedem Start:
1. Host/IP des u-OS Data Hub hier eintragen (`HOST`, `PORT`).
2. Im u-OS Control Center → Identity & access → Clients → Add client einen
   Provider-Client anlegen und dessen `CLIENT_ID`, `CLIENT_SECRET` hier eintragen.
3. Falls du mehrere Provider betreibst, `PROVIDER_ID`/`CLIENT_NAME` entsprechend wählen.
"""

from .models import VariableAccess, VariableDefinitionModel, VariableType

HOST = "192.168.10.108"
PORT = 49360
PROVIDER_ID = "sampleprovider"
PUBLISH_INTERVAL_SECONDS = 1.0

CLIENT_NAME = "sampleprovider"
CLIENT_ID = "76df2b35-a7e7-4ba5-9e10-06b8a24a0b02"
CLIENT_SECRET = "WcKIUVPCf59fJHmcADwhY5zojA"

TOKEN_ENDPOINT = f"https://{HOST}/oauth2/token"

# Keys appear exactly like this inside the u-OS Data Hub tree.
VARIABLE_DEFINITIONS = [
    VariableDefinitionModel(
        1,
        "digital_nameplate.manufacturer_name",
        VariableType.STRING,
        VariableAccess.READ_ONLY,
    ),
    VariableDefinitionModel(
        2,
        "digital_nameplate.serial_number",
        VariableType.STRING,
        VariableAccess.READ_ONLY,
    ),
    VariableDefinitionModel(
        3,
        "digital_nameplate.year_of_construction",
        VariableType.INT64,
        VariableAccess.READ_ONLY,
    ),
    VariableDefinitionModel(
        4,
        "digital_nameplate.hardware_version",
        VariableType.STRING,
        VariableAccess.READ_ONLY,
    ),
    VariableDefinitionModel(
        5,
        "diagnostics.status_text",
        VariableType.STRING,
        VariableAccess.READ_WRITE,
    ),
    VariableDefinitionModel(
        6,
        "diagnostics.error_count",
        VariableType.INT64,
        VariableAccess.READ_WRITE,
    ),
    VariableDefinitionModel(
        7,
        "diagnostics.temperature",
        VariableType.FLOAT64,
        VariableAccess.READ_ONLY,
    ),
    VariableDefinitionModel(
        8,
        "diagnostics.is_running",
        VariableType.BOOLEAN,
        VariableAccess.READ_WRITE,
    ),
]
