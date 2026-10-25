"""Alert Map Proxy Server - Neptun Provider - Constants."""

import os

# Secure stream endpoint for Neptun engine platform
URI = os.getenv("PROXY_ALERT_URL", "wss://neptun.in.ua/api/v1/stream")

# --- PLACEHOLDER FOR NEPTUN SPECIFIC HEADERS ---
# Add Neptun's binary markers or data types here when available
