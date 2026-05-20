"""Constants for the Dacia Spring Connect integration."""

DOMAIN = "dacia_spring_connect"
DEFAULT_SCAN_INTERVAL = 300  # seconds
MIN_SCAN_INTERVAL = 30  # seconds

# Config entry keys
CONF_LOCALE = "locale"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ACCOUNT_ID = "account_id"
CONF_VIN = "vin"

# Default values
DEFAULT_LOCALE = "fr_FR"

# Platforms
PLATFORMS = [
    "sensor",
    "binary_sensor",
    "climate",
    "device_tracker",
    "select",
    "button",
]

# Coordinator update key names
DATA_COORDINATOR = "coordinator"

# Renault API model keys
MODEL_SUPPORTS_BATTERY = "battery_status"
MODEL_SUPPORTS_HVAC = "hvac_status"
MODEL_SUPPORTS_LOCATION = "location"
MODEL_SUPPORTS_CHARGE_MODE = "charge_mode"
MODEL_SUPPORTS_COCKPIT = "cockpit"
