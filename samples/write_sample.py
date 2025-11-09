from __future__ import annotations

# Sample by IoTUeli – https://iotueli.com | LinkedIn: iotueli

import argparse
import asyncio
import pathlib
import sys

SRC_PATH = pathlib.Path(__file__).resolve().parent.parent
if str(SRC_PATH / "src") not in sys.path:
    sys.path.insert(0, str(SRC_PATH / "src"))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from iotueli_sample.config import PROVIDER_ID
from provider_cli import open_connection, write_value


def parse_args():
    parser = argparse.ArgumentParser(description="Einfacher Write-Befehl")
    parser.add_argument("--provider", default=PROVIDER_ID, help="Provider-ID")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--key", help="Variable-Key (nur READ_WRITE Variablen)")
    target.add_argument("--id", type=int, help="Variable-ID")
    parser.add_argument("--value", required=True, help="Wert als String")
    return parser.parse_args()


async def async_main():
    args = parse_args()
    conn = await open_connection("write-sample")
    try:
        await write_value(conn, args.provider, args.key, args.id, args.value)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(async_main())
