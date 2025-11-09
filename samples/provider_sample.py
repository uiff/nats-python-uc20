from __future__ import annotations

# Sample by IoTUeli – https://iotueli.com | LinkedIn: iotueli

import asyncio
import pathlib
import sys

SRC_PATH = pathlib.Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from iotueli_sample.provider_app import ProviderApp
from provider import build_runtime


async def main() -> None:
    runtime = build_runtime()
    provider = ProviderApp(runtime)
    await provider.start()
    print("Sample provider läuft – Ctrl+C zum Beenden.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Beende Provider…")
    finally:
        await provider.stop()


if __name__ == "__main__":
    asyncio.run(main())
