# Sample Scripts Overview

This folder bundles three small entry points that demonstrate die wichtigsten Workflows:

1. **Provider** – startet den Demo-Provider mit den Variablen sowie Zugangsdaten aus `src/iotueli_sample/config.py` (vorher dort Host/IP und Credentials eintragen).
2. **Read** – liest einen Snapshot bzw. geänderte Werte eines Providers.
3. **Write** – schreibt einen Wert auf eine beschreibbare Variable und validiert das Ergebnis.

## Voraussetzungen

- Virtuelle Umgebung aktiv (`source .venv/bin/activate` oder gleichwertig).
- Die OAuth-Daten (`CLIENT_ID`, `CLIENT_SECRET`, `HOST`, `PROVIDER_ID`) trägst du in `src/iotueli_sample/config.py` ein, nachdem du im u-OS Control Center → *Identity & access → Clients* auf **Add client** geklickt und einen neuen Client erstellt hast.
- NATS-Port ist aus der Steuerung erreichbar.

## 1. Provider starten

```
(.venv) python3 samples/provider_sample.py
```

Der Provider publiziert alle Variablen im Sekundentakt (Intervall über `PUBLISH_INTERVAL_SECONDS` in `config.py`). Beenden mit `Ctrl+C`.

## 2. Werte lesen

```
(.venv) python3 samples/read_sample.py --provider sampleprovider --key diagnostics.temperature
```

- `--provider` kann auf jeden registrierten Provider zeigen (`u_os_adm`, …).
- Statt `--key` kann auch `--id 6` (numerische Variable-ID) verwendet werden.
- Ohne Parameter wird der Standard-Provider aus `config.py` gelesen.

Der Read-Sample ruft exakt einmal einen Snapshot ab. Für stetige Überwachung nutze `provider_consumer.py`.

## 3. Werte schreiben

```
(.venv) python3 samples/write_sample.py --provider sampleprovider --key diagnostics.status_text --value Running
```

- Nur Variablen mit Access *READ_WRITE* akzeptieren Schreibbefehle.
- `--id` funktioniert ebenfalls.
- Nach dem Schreiben liest das Skript automatisch den neuen Wert zur Kontrolle.

## Weitere Provider auslesen

1. Verfügbare Provider per Registry prüfen:
   ```
   python3 provider_cli.py list-providers
   ```
2. Definition ansehen:
   ```
   python3 provider_cli.py describe --provider u_os_adm
   ```
3. Danach `read_sample.py` oder `provider_consumer.py --provider u_os_adm --key <key>` verwenden.

## Troubleshooting

- *`nats: permissions violation …`*: Token besitzt keine Rechte auf den genannten Subject-Namen → Provider-ID in `config.py` zurücksetzen oder andere Credentials verwenden.
- *Keine Werte im Snapshot*: Key/ID existiert nicht beim gewählten Provider. Definition mit `provider_cli.py describe` prüfen.
- *Provider erscheint nicht im Data Hub UI*: Provider muss laufen und erfolgreich eine Definition publizieren. Konsolen-Ausgabe von `provider_sample.py` zeigt, ob Registrierung klappt.
