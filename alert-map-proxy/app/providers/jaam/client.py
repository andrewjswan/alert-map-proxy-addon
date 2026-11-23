"""Alert Map Proxy Server - JAAM Provider - Client."""

import asyncio
import json
import logging
import random
import time
import uuid
from datetime import datetime

import config
import websockets

from . import constants, processor

# Initialize module-level logger
LOGGER = logging.getLogger(__name__)


def get_device_uuid() -> str:
    """Generate a deterministic UUID from the hardware MAC address."""
    mac_int = uuid.getnode()
    mac_hex = f"{mac_int:012x}"
    return str(uuid.uuid5(uuid.NAMESPACE_OID, mac_hex))


async def receive_messages(websocket: websockets.WebSocketClientProtocol) -> None:
    """Receive and parse incoming JAAM stream messages."""
    LOGGER.info("🎧 [JAAM] Pipeline active. Listening to hybrid text/binary stream channel...")

    while True:
        try:
            # Enforce an internal NN-second read timeout loop to consistently check the Watchdog window
            # This prevents the system from hanging indefinitely if the remote server stays silent
            message = await asyncio.wait_for(websocket.recv(), timeout=config.SOCKET_READ_TIMEOUT_SEC)
            if isinstance(message, bytes):
                if not message:
                    continue
                header_byte = message[0]
                config.last_heartbeat = datetime.now(config.CURRENT_TZ)

                # --- TRANSPORT LAYER FILTERING GATE ---
                # Safely skip environmental data and firmware binary OTA transmission blocks
                if header_byte in (
                    constants.TYPE_WEATHER_BATCH,
                    constants.TYPE_ENERGY_BATCH,
                    constants.TYPE_RADIATION_BATCH,
                    constants.TYPE_FIRMWARE_UPDATE_BETA_BATCH,
                    constants.TYPE_FIRMWARE_UPDATE_PROD_BATCH,
                ):
                    LOGGER.debug("🐛 [JAAM] Non-alert payload %s skipped safely.", hex(header_byte))
                    continue

                # Core operational logging for verified alert channels
                LOGGER.debug("🐛 [JAAM] Binary payload. Header: %s (Size: %dB)", hex(header_byte), len(message))
                LOGGER.debug("🐛 [JAAM] Binary payload. Message: %s", message)

                try:
                    # Lock the HTTP worker threads before mutating config.state_cache
                    config.cache_ready_event.clear()

                    # --- DYNAMIC DISPATCH ROUTING LIFECYCLE ---
                    if header_byte == constants.TYPE_ALERTS_BATCH:
                        # Payload 0xA1: Full national snapshot; uses 5-byte header shift (1B type + 4B hashes)
                        processor.process_jaam_batch(message, offset=5, notify=False)
                        config.state_cache["updated"] = datetime.now(config.CURRENT_TZ).isoformat()
                        LOGGER.info("⚡ [JAAM] Memory Sync: Full state snapshot tree refreshed.")
                    elif header_byte == constants.TYPE_NOTIFICATIONS_BATCH:
                        # Payload 0xA2: Fast real-time tactical changes; uses 1-byte header shift (only type)
                        processor.process_jaam_batch(message, offset=1, notify=True)
                        config.state_cache["updated"] = datetime.now(config.CURRENT_TZ).isoformat()
                        LOGGER.info("⚡ [JAAM] Memory Sync: Operational notification applied.")
                except Exception:
                    LOGGER.exception("💥 [JAAM] Internal error inside frame decoding processor:")
                finally:
                    # Always release the lock so the web server can serve the updated layout
                    config.cache_ready_event.set()

        except TimeoutError:
            # The read timed out, check if the global heartbeat has crossed the NN-minute fatal limit
            minutes_since_pulse = (datetime.now(config.CURRENT_TZ) - config.last_heartbeat).total_seconds() / 60.0
            if minutes_since_pulse > config.HEALTH_FATAL_RECONNECT_MIN:
                LOGGER.warning(
                    "🚨 [JAAM] Watchdog: No telemetry data for %d minutes. Force-dropping stalled socket connection...",
                    int(minutes_since_pulse),
                )
                # Exit the read loop so the context manager cleanly closes the socket and triggers reconnect
                return
            continue


async def run_provider() -> None:
    """Execute the main lifecycle loop for the JAAM provider."""
    apps_uuid = get_device_uuid()
    LOGGER.info("🤖 Booting JAAM client engine. ID: %s FW: %s", apps_uuid, constants.CURRENT_VERSION)

    hello_msg = "hello:" + json.dumps(
        {
            "service_id": "alert-map-proxy",
            "client_id": apps_uuid,
            "name": "Alert Map Proxy",
            "website": "https://github.com/andrewjswan/alert-map-proxy-addon",
            "contact": "@andrewjswan",
            "version": constants.CURRENT_VERSION,
        },
        ensure_ascii=False,
    )

    delay = config.PIPELINE_RECONNECT_DELAY_SEC
    while True:
        started = time.monotonic()
        try:
            # Block HTTP requests immediately on startup or when connection drops
            config.cache_ready_event.clear()

            async with websockets.connect(
                constants.URI,
                ping_interval=None,
            ) as websocket:
                LOGGER.info("✅ [JAAM] Core pipeline linked into remote JAAM server architecture stream!")
                config.last_heartbeat = datetime.now(config.CURRENT_TZ)

                processor.region_cache.clear()
                processor.reset_jaam_cache()
                LOGGER.info("🧹 [JAAM] Telemetry state and region caches successfully synchronized to pristine state.")

                await websocket.send(hello_msg)

                LOGGER.info("🚀 [JAAM] Client handshake verified. Pipeline online for JAAM.")
                # Read loop execution keeps context busy here
                await receive_messages(websocket)

        except websockets.exceptions.ConnectionClosed as e:
            LOGGER.warning("⚠️ [JAAM] Pipeline connection closed by server. Code: %d, Reason: '%s'", e.code, e.reason)
            if e.rcvd and e.rcvd.code in (1008, 4403):
                delay = 300.0

        except Exception:
            LOGGER.exception("💥 [JAAM] Connection lost or error:")

        finally:
            # Safely release HTTP threads lock if connection routine crashes or breaks
            config.cache_ready_event.set()

        # --- MANDATORY EXPONENTIAL BACKOFF WITH JITTER AND RESET LOGIC ---
        connection_duration = time.monotonic() - started
        if connection_duration > 60.0:  # noqa: PLR2004
            # Reset backoff back to default configuration if connection survived long enough
            delay = config.PIPELINE_RECONNECT_DELAY_SEC

        # Calculate random jitter factor based on current execution delay
        calculated_delay = delay * random.uniform(0.8, 1.2)  # noqa: S311
        LOGGER.info("🔄 [JAAM] Reconnecting in %d seconds...", calculated_delay)
        await asyncio.sleep(calculated_delay)

        # Multiply base delay for the next incremental fallback iteration if failures persist
        delay = min(delay * 2.0, 300.0)
