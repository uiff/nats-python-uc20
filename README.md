# IoTUeli Minimal Data Hub Samples

Ordner mit komplett eigenständigen Samples für einen einfachen Provider und optionalen Consumer zum u-OS Data Hub auf dem Gerät `192.168.10.141`.

## 1. Vorbereitungen auf der Steuerung

1. **OAuth-Clients anlegen**: Im u-OS Control Center (Screenshot siehe `docs/control-center-clients.png`) zu *Identity & access → Clients* wechseln und oben rechts auf **Add client** drücken.
   - **Provider** `sampleprovider`: Access `hub.variables` → Rolle **Provide**
   - **Consumer** `sampleconsumer`: Access `hub.variables` → Rolle **ReadWrite** (oder Read)
   - Die zugehörigen Client ID & Secrets notieren.
2. **Token-Test**:
   ```bash
   curl -vk -u '<CLIENT_ID>:<CLIENT_SECRET>' \
        -d 'grant_type=client_credentials&scope=hub.variables.provide' \
        https://192.168.10.141/oauth2/token
   ```
   Erfolgreich ist der Test, wenn ein `access_token` zurückkommt. Für den Consumer analog mit `scope=hub.variables.readwrite` testen.

## 2. Projekt lokal vorbereiten

**Ganz wichtig:** Python-Abhängigkeiten werden ausschließlich innerhalb einer lokalen virtuellen Umgebung installiert, damit dein System sauber bleibt.

```bash
cd ~/App/nats-python
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> Die virtuelle Umgebung (`.venv`) liegt damit direkt im Projektordner und muss vor jedem Kommando aktiviert sein (`source .venv/bin/activate`).
> Die Datei `requirements.txt` bringt alle notwendigen Bibliotheken mit – inklusive `nats-py`, `aiohttp`, `flatbuffers` usw. – damit du ohne weitere Downloads sofort mit der NATS-Kommunikation loslegen kannst.

## 3. Konfiguration anpassen

Alle verbindungs- und credentialspezifischen Angaben liegen **nur** in `src/iotueli_sample/config.py`.

| Feld                | Bedeutung                                                                 |
|---------------------|----------------------------------------------------------------------------|
| `HOST` / `PORT`     | IP-Adresse und NATS-Port deiner Steuerung                                 |
| `PROVIDER_ID`       | Anzeigename des Providers im Data Hub                                     |
| `CLIENT_NAME`       | Frei wählbarer Client-Name (sollte zum Provider passen)                    |
| `CLIENT_ID/SECRET`  | Werte aus dem Control Center → Clients                                    |
| `VARIABLE_DEFINITIONS` | Liste der Variablen, die im Data Hub erscheinen sollen                  |

> Nach jeder Änderung in `config.py` Provider/Consumer neu starten.

## 3. Provider starten

1. Datei `provider.py` öffnen und die Platzhalter `DEINE_*` durch die echten Werte (`Client ID`, `Client Secret`, ggf. Provider-ID/Host/Port) ersetzen.
2. Provider ausführen:
   ```bash
   source .venv/bin/activate
   python provider.py
   ```
3. Ausgabe: `Provider gestartet – Strg+C zum Beenden.` In der Data-Hub-Weboberfläche erscheint unter *Providers* nun `demo-provider`.

## 4. Consumer starten (optional)

1. Datei `consumer.py` analog anpassen (Clientdaten, ggf. Provider-ID).
2. In zweitem Terminal (mit aktivierter `.venv`):
   ```bash
   python consumer.py
   ```
3. Das Skript gibt zunächst die Momentaufnahme aus und schreibt bei Änderungen die neuen Werte ins Terminal.

## 5. Troubleshooting

- **401 `invalid_client`** – Client-ID/Secret oder Scope stimmt nicht. Token-Test überprüfen.
- **`permissions violation`** – Dem OAuth-Client fehlt die Rolle `Provide` bzw. `Read/ReadWrite`. Im Control Center korrigieren und Skript neu starten.
- **`no responders`** – Provider läuft nicht oder Provider-ID im Consumer stimmt nicht. Provider neu starten und sicherstellen, dass beide die gleiche `PROVIDER_ID` verwenden.
- **`No module named 'weidmueller'`** – Skripte nur aus dem Ordner `nats-python` mit aktivierter `.venv` starten; dort wird das `src/`-Verzeichnis automatisch auf den `PYTHONPATH` gesetzt.
- **Self-signed TLS** – Die Skripte deaktivieren die Zertifikatsprüfung (`verify=False`). Für produktive Umgebungen sollte ein echtes Zertifikat hinterlegt werden.

Viel Erfolg! Änderungen an Konfiguration oder Variablen einfach in den jeweiligen Dateien anpassen und den Provider neu starten.
