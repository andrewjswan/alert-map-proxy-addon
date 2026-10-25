"""Alert Map Proxy Server - JAAM Provider - Client."""

import asyncio
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


def get_dynamic_chip_id() -> str:
    """Generate a hardware-compliant client hex token."""
    mac_int = uuid.getnode()
    mac_bytes = mac_int.to_bytes(6, byteorder="big")
    padded_mac = mac_bytes + b"\x00\x00"
    efuse_mac = int.from_bytes(padded_mac, byteorder="little")
    high_bits = (efuse_mac >> 32) & 0xFFFFFFFF
    low_bits = efuse_mac & 0xFFFFFFFF
    return f"{high_bits:04x}{low_bits:04x}"[:12]


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
                # Raising an exception breaks the current execution block and forces a clean reconnection lifecycle
                raise websockets.exceptions.ConnectionClosed(None, None) from None
            continue


async def run_provider() -> None:
    """Execute the main lifecycle loop for the JAAM provider."""
    chip_id = get_dynamic_chip_id()
    LOGGER.info("🤖 Booting JAAM client engine. ID: %s FW: %s", chip_id, constants.CURRENT_VERSION)

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

                await websocket.send(f"chip_id:{chip_id}")
                await websocket.send(f"firmware:{constants.CURRENT_VERSION}")

                LOGGER.info("🚀 [JAAM] Client handshake verified. Pipeline online for JAAM.")
                # Read loop execution keeps context busy here
                await receive_messages(websocket)

        except websockets.exceptions.ConnectionClosed as e:
            LOGGER.warning("⚠️ [JAAM] Pipeline connection closed by server. Code: %d, Reason: '%s'", e.code, e.reason)

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
