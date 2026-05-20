# Dacia Spring Connect for Home Assistant

Bring your **Dacia Spring** into Home Assistant. Monitor battery, range, and charging state, set a charge limit that stops automatically, warm up the cabin before you leave, and see your car on the map — all without leaving the HA dashboard.

> Uses the same unofficial API as the official MyDacia/MyRenault app, via the [`renault-api`](https://github.com/hacf-fr/renault-api) library.

---

## What you get

### Sensors
| | Entity | What it shows |
|---|---|---|
| 🔋 | **Battery Level** | Current state of charge (%) |
| 🛣️ | **Battery Autonomy** | Estimated remaining range (km) |
| ⏱️ | **Charging Remaining Time** | Minutes until fully charged |
| ⚡ | **Charge Status** | e.g. *Charging*, *Charge ended*, *Not charging* |
| 📍 | **Mileage** | Total odometer reading (km) |

### Controls
| | Entity | What it does |
|---|---|---|
| 🎛️ | **Charge Limit** | Set a target % (50–100). Charging stops automatically when reached, and restarts if you raise the limit while plugged in. |
| ❄️ | **Start Pre-conditioning** | Warms/cools the cabin remotely. The car stops automatically after ~10 minutes. |
| ▶️ | **Start Charging** | Starts charging immediately. |
| ⏹️ | **Stop Charging** | Stops charging immediately. |
| 🔄 | **Refresh Location** | Asks the car to update its GPS position. |

### Status indicators
| | Entity | What it shows |
|---|---|---|
| 🔌 | **Plugged In** | Whether the charging cable is connected |
| ⚡ | **Charging** | Whether the battery is actively charging |
| 🌡️ | **Pre-conditioning Active** | Whether cabin heating/cooling is running |
| 🗺️ | **Location** | Live position on the HA map |

---

## Installation

### Via HACS (recommended)

1. In Home Assistant, open **HACS → Integrations**.
2. Click the three-dot menu (⋮) → **Custom repositories**.
3. Enter `https://github.com/bogdanadnan/DaciaSpringConnect` and set the category to **Integration**.
4. Find *Dacia Spring Connect* in HACS and click **Install**.
5. Restart Home Assistant.

### Manual

Download or clone this repository and copy the `custom_components/dacia_spring_connect` folder into your Home Assistant `config/custom_components/` directory, then restart.

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Dacia Spring Connect**.
3. Sign in with your **MyDacia / MyRenault** credentials and select your country/region.
4. Choose your Kamereon account and then your vehicle.

That's it — the integration will start polling your car and all entities will appear under a single device.

---

## Notes

- **Charge Limit**: the configured percentage is remembered across Home Assistant restarts. If you raise the limit while the car is plugged in and stopped, charging restarts automatically.
- **Pre-conditioning**: the Dacia Spring does not support cancelling pre-conditioning remotely — it always runs for a fixed period (~10 min) and stops on its own.
- **Location**: the car only updates its GPS position when driven; use *Refresh Location* to request a fresh reading.

---

## Disclaimer

This project is not affiliated with, endorsed by, or connected to Renault or Dacia. Use at your own risk.

## License

MIT
