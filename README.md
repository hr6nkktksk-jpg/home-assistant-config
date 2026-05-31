# Home Assistant Konfiguration — Uetikon am See

Dieses Repository enthält die Home Assistant Konfiguration und dokumentiert, wie alle beteiligten Systeme zusammenspielen.

---

## Systemübersicht

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Synology NAS (192.168.2.49)                  │
│                    /volume1/docker/  (Docker-Root)                  │
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐   ┌────────────────┐  │
│  │  homeassistant   │    │   claude-code     │   │  code-server   │  │
│  │  :8124 → :8123   │    │  (Node.js 20)    │   │  (VS Code Web) │  │
│  │                  │    │                  │   │                │  │
│  │ /config          │    │ /config          │   │                │  │
│  │  = .../ha/config │    │  = home-dir      │   │                │  │
│  │                  │    │ /workspace       │   │                │  │
│  │ HA 2026.4.4      │    │  = /volume1/     │   │                │  │
│  └──────────────────┘    │    docker/       │   └────────────────┘  │
│           ▲              └──────────────────┘                       │
│           │ reload_all            │                                  │
│           │ (REST API)            │ post-commit hook                 │
│           │                       │ kopiert geänderte Dateien        │
│           └───────────────────────┘                                 │
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐                       │
│  │     adguard      │    │      squid       │  172.21.0.2:3128      │
│  │   (DNS/Ad-Block) │    │  (HTTP-Proxy für │  → Internet-Zugang    │
│  └──────────────────┘    │   claude-code)   │  für claude-code      │
│                          └──────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ git push
                                    ▼
                    ┌───────────────────────────────┐
                    │  GitHub                        │
                    │  hr6nkktksk-jpg/               │
                    │  home-assistant-config         │
                    └───────────────────────────────┘
```

---

## Komponenten im Detail

### 1. Synology NAS

- **IP-Adresse:** `192.168.2.49`
- **Docker-Root:** `/volume1/docker/`
- Alle Container werden per `docker-compose` aus `/volume1/docker/compose.yaml` gestartet

**Wichtige Verzeichnisse auf dem NAS:**

| NAS-Pfad | Verwendung |
|----------|-----------|
| `/volume1/docker/homeassistant-dev/config/` | HA-Konfigurationsdateien |
| `/volume1/docker/claude-code/projekte/` | Claude Code Arbeitsverzeichnisse |
| `/volume1/docker/compose.yaml` | Docker Compose Stack |

---

### 2. Home Assistant Container

```yaml
# aus compose.yaml
homeassistant:
  image: ghcr.io/home-assistant/home-assistant:stable
  ports: "8124:8123"
  volumes:
    - /volume1/docker/homeassistant-dev/config:/config
```

- **Weboberfläche:** `http://192.168.2.49:8124`
- **Version:** 2026.4.4
- **Config-Pfad (NAS):** `/volume1/docker/homeassistant-dev/config/`
- **Config-Pfad (im Container):** `/config/`
- **Config-Pfad (aus Claude Code):** `/workspace/homeassistant-dev/config/`

#### Installierte Custom Components

| Integration | Quelle | Zweck |
|-------------|--------|-------|
| `ecowitt` | Custom Component (in diesem Repo) | GW1200-Patch: ergänzt fehlendes `model`-Feld |
| `swissweather` | HACS (`izacus/hass-swissweather`) | MeteoSwiss Wettervorhersage |
| `hacs` | HACS 2.0.5 | Marketplace für Custom Integrations |

#### Konfigurierte Integrationen

| Integration | Entität | Daten |
|-------------|---------|-------|
| MeteoSwiss (swissweather) | `weather.meteoswiss_at_8707_wae_*` | PLZ 8707, Station WAE (Wädenswil) |
| Ecowitt | `sensor.gw1200a_*` | GW1200A `80:F1:B2:E6:8D:EC` |
| Scrape-Sensoren | `sensor.meteoswiss_uetikon_*` | MeteoSwiss API direkt |

#### Dashboards

| URL-Pfad | Name | Inhalt |
|----------|------|--------|
| `/lovelace` | Overview | Standard HA Dashboard (leer) |
| `/wetter-uetikon` | Wetter Uetikon | MeteoSwiss Wetterdaten |
| `/ecowitt-gw1200` | Ecowitt GW1200 | Sensoren des GW1200-Gateways |

---

### 3. Claude Code Container

```yaml
# aus /workspace/claude-code/compose.yaml
claude-code:
  image: node:20
  volumes:
    - /volume1/docker/claude-code/projekte:/projekte
  environment:
    - HTTP_PROXY=http://172.21.0.2:3128
    - HTTPS_PROXY=http://172.21.0.2:3128
```

- Claude Code läuft als interaktive KI-Entwicklungsumgebung
- Zugang zum Internet über den **Squid-Proxy** (`172.21.0.2:3128`)
- Internes Docker-Netzwerk `claude-netz` (kein direkter Außenzugang)
- Das Verzeichnis `/workspace/` im Container entspricht `/volume1/docker/` auf dem NAS — dadurch hat Claude Code Zugriff auf die HA-Config und alle anderen Container-Daten

**Wichtige Pfade im Claude Code Container:**

| Pfad im Container | entspricht auf NAS |
|-------------------|--------------------|
| `/workspace/homeassistant-dev/config/` | `/volume1/docker/homeassistant-dev/config/` |
| `/config/workspace/home-assistant-config/` | Git-Repository (Arbeitsverzeichnis) |

#### Git-Alias `save`

```sh
git save
# entspricht:
git add -A && git commit -m "$(date +%Y-%m-%d\ %H:%M:%S)" && git push origin main
```

Stages alle Änderungen, committet mit Zeitstempel und pusht zu GitHub.

---

### 4. Code-Server

- VS Code im Browser, läuft als eigener Container auf dem NAS
- Ermöglicht manuelle Bearbeitung von Dateien über die Browser-Oberfläche
- Teilt dasselbe Dateisystem wie Claude Code (über NAS-Volumes)

---

### 5. GitHub Repository

- **URL:** `https://github.com/hr6nkktksk-jpg/home-assistant-config`
- **Branch:** `main`
- Dient als Versionskontrolle und Backup der HA-Konfiguration

---

## Workflow: Änderung an der HA-Konfiguration

```
┌──────────────────────────────────────────────────────────┐
│  1. Datei bearbeiten                                      │
│     Claude Code oder code-server                          │
│     Pfad: /config/workspace/home-assistant-config/        │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  2. git save                                              │
│     → git add -A                                          │
│     → git commit -m "2026-05-31 10:00:00"                │
│     → git push origin main  (→ GitHub)                   │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼ post-commit Hook
┌──────────────────────────────────────────────────────────┐
│  3. Automatisches Deployment                              │
│     Geänderte Dateien werden kopiert nach:                │
│     /workspace/homeassistant-dev/config/                  │
│     (= /volume1/docker/homeassistant-dev/config/ auf NAS) │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼ REST API
┌──────────────────────────────────────────────────────────┐
│  4. HA Konfiguration neu laden                            │
│     POST http://192.168.2.49:8124/                        │
│          api/services/homeassistant/reload_all            │
│     → HA übernimmt Änderungen ohne Neustart               │
└──────────────────────────────────────────────────────────┘
```

### post-commit Hook (`.git/hooks/post-commit`)

Der Hook liest Konfiguration aus dem lokalen Git-Config:

```sh
git config --local ha.url    # http://192.168.2.49:8124
git config --local ha.token  # Long-Lived Access Token (nicht im Repo!)
git config --local ha.dest   # /workspace/homeassistant-dev/config (Standard)
```

**Sicherheitshinweis:** Der HA-Token ist nur in `.git/config` (lokal) gespeichert und wird **nicht** zu GitHub gepusht.

---

## Repository-Struktur

```
home-assistant-config/
├── configuration.yaml              # Haupt-HA-Konfiguration
├── packages/
│   └── meteoswiss_uetikon.yaml    # REST-Sensoren & Templates (MeteoSwiss)
├── dashboards/
│   └── wetter_uetikon.yaml        # Lovelace YAML-Dashboard (Referenz)
├── custom_components/
│   └── ecowitt/                   # Gepatchte Ecowitt-Integration
│       ├── __init__.py            # Patch: ergänzt fehlendes model-Feld
│       ├── manifest.json          # Version 2025.9.2
│       └── *.py / *.json          # Restliche Dateien = HA 2026.4.4 Stock
└── .claude/
    └── settings.json              # Claude Code: bypassPermissions
```

---

## Ecowitt GW1200 — Besonderheit

Das Gerät (MAC `80:F1:B2:E6:8D:EC`) sendet kein `model`-Feld im POST-Body, das `aioecowitt` ≥ 2024.x erwartet. Die Custom Component `custom_components/ecowitt/__init__.py` patcht die Library beim Laden:

```python
# Patch in custom_components/ecowitt/__init__.py
def _patched_extract_station(data):
    if "model" not in data:
        data["model"] = data.get("stationtype", "GW1200A")
    return _orig_extract_station(data)
```

Das GW1200 ist konfiguriert, Daten alle 60 Sekunden per HTTP POST zu senden:
- **Ziel:** `http://192.168.2.49:8124/api/webhook/7827c51e98059ca56d799db39fe649e9`
- **Protokoll:** Ecowitt

---

## Netzwerk-Übersicht

| Dienst | IP / Port | Protokoll |
|--------|-----------|-----------|
| Home Assistant | `192.168.2.49:8124` | HTTP |
| AdGuard | NAS-intern | DNS |
| Squid Proxy | `172.21.0.2:3128` | HTTP-Proxy |
| Ecowitt GW1200 | `192.168.2.192` | HTTP (Push) |
| GitHub | `github.com` | HTTPS (via Proxy) |
| MeteoSwiss API | `app-prod-ws.meteoswiss-app.ch` | HTTPS (via Proxy) |
