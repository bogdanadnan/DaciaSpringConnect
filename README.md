# Dacia Spring Connect — Home Assistant Custom Integration

A custom [Home Assistant](https://www.home-assistant.io/) integration for the **Dacia Spring Connect** electric vehicle, powered by the [`renault-api`](https://github.com/hacf-fr/renault-api) library.

## Features

| Platform | Entity | Description |
|---|---|---|
| `sensor` | Battery Level | State of charge (%) |
| `sensor` | Battery Autonomy | Remaining range (km) |
| `sensor` | Charging Remaining Time | Minutes to full charge |
| `sensor` | Charge Status | Current charging state |
| `sensor` | Mileage | Total odometer reading (km) |
| `binary_sensor` | Plugged In | Whether the cable is connected |
| `binary_sensor` | Charging | Whether the battery is actively charging |
| `binary_sensor` | Pre-conditioning Active | Whether HVAC is running |
| `climate` | Pre-conditioning | Start/stop cabin pre-conditioning with target temperature |
| `device_tracker` | Location | Live GPS position |
| `number` | Charge Limit | Auto-stop charging at this battery % (50–100, step 5) |
| `button` | Start Charging | Trigger an immediate charge start |
| `button` | Stop Charging | Trigger an immediate charge stop |
| `button` | Refresh Location | Force a GPS location update |

## Installation

### HACS (recommended)

1. Open HACS → **Integrations** → **⋮** → **Custom repositories**.
2. Add `https://github.com/bogdanadnan/DaciaSpringConnect` with category **Integration**.
3. Search for *Dacia Spring Connect* and install.
4. Restart Home Assistant.

### Manual

Copy the `custom_components/dacia_spring_connect` folder into your HA `config/custom_components/` directory and restart.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Dacia Spring Connect**.
3. Follow the three-step wizard:
   - Enter your **MyRenault** email and password, and your locale (e.g. `fr_FR`).
   - Select the **Kamereon account**.
   - Select the **vehicle** by VIN.

## Development

### Prerequisites

- Python ≥ 3.12
- A [devcontainer](https://containers.dev/)-capable editor (VS Code recommended)

### Quick start

```bash
# Create virtual environment and install dev dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest
```

### Dev Container

Open the workspace in VS Code and select **Reopen in Container** when prompted. The container mounts `custom_components/dacia_spring_connect` directly into a running Home Assistant instance.

## Disclaimer

This project is not affiliated with, endorsed by, or connected to Renault or Dacia.
Use at your own risk.

## License

MIT
