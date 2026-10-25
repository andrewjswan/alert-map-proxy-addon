"""Alert Map Proxy Server - JAAM Provider - Constants."""

import os

# WebSocket connection URL for JAAM platform
URI = os.getenv("PROXY_ALERT_URL", "ws://ws.jaam.net.ua:80/data_fusion_v1")

# Handshake configuration properties
CURRENT_VERSION = f"AMP-{os.getenv('PROXY_VERSION', '2026.10.0')}"  # JAAM firmware version

# fmt: off

# --- BINARY ARCHITECTURE FUSION HEADERS ---
TYPE_ALERTS_BATCH               = 0xA1   # 161: Main stream for country-wide alert snapshots
TYPE_NOTIFICATIONS_BATCH        = 0xA2   # 162: Operational real-time regional notification events
TYPE_WEATHER_BATCH              = 0xA3   # 163: Dynamic country-wide meteorological temperature updates
TYPE_ENERGY_BATCH               = 0xA4   # 164: National power grid status and outage tracking logs
TYPE_RADIATION_BATCH            = 0xA5   # 165: Raw background radiation tracking (nSv/h)
TYPE_FIRMWARE_UPDATE_BETA_BATCH = 0xA6   # 166: Beta firmware binary OTA update transmission packets
TYPE_FIRMWARE_UPDATE_PROD_BATCH = 0xA7   # 167: Production firmware binary OTA update transmission packets

# --- OFFICIAL ALERTMODES ENUM COMPLIANT MASKS ---
BIT_LEGACY_ALERT = 1 << 0       # 1: Discarded legacy bit layout
BIT_ARTILLERY    = 1 << 1       # 2: Artillery hazard strike warning
BIT_URBAN        = 1 << 2       # 4: Localized proximity urban combat danger
BIT_CHEMICAL     = 1 << 3       # 8: Localized chemical event threshold warning
BIT_NUCLEAR      = 1 << 4       # 16: Nuclear or radiation escalation event
BIT_DRONES       = 1 << 5       # 32: UAV / Shahed tactical deployment warning
BIT_MISSILES     = 1 << 6       # 64: Guided/Cruise missile tracking indicator
BIT_KABS         = 1 << 7       # 128: Tactical guided aerial bomb warning layer
BIT_BALLISTIC    = 1 << 8       # 256: High-altitude strategic ballistic launch confirmed
BIT_EXPLOSION    = 1 << 9       # 512: Verified dynamic kinetic impact event detected
BIT_RECON_DRONES = 1 << 10      # 1024: Strategic surveillance reconnaissance drone active
BIT_ALERT_LOW    = 1 << 11      # 2048: Silent/Low-level air alert status trigger
BIT_ALERT_HIGH   = 1 << 12      # 4096: High-level primary air alert siren trigger

# fmt: on
