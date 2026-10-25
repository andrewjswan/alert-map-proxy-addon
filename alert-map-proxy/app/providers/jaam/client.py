import asyncio
import json
import uuid
import random
import time
import websockets
from datetime import datetime
import config
import logging
from . import constants
from . import processor

# Initialize module-level logger
LOGGER = logging.getLogger(__name__)

def get_dynamic_chip_id():
    """ Generates a hardware-compliant client hex token matching the exact ESP32 eFuse MAC formatting register output logic. """
    mac_int = uuid.getnode()
    mac_bytes = mac_int.to_bytes(6, byteorder='big')
    padded_mac = mac_bytes + b'\x00\x00'
    efuse_mac = int.from_bytes(padded_mac, byteorder='little')
    high_bits = (efuse_mac >> 32) & 0xFFFFFFFF
    low_bits = efuse_mac & 0xFFFFFFFF
    return f"{high_bits:04x}{low_bits:04x}"[:12]

async def receive_messages(websocket):
    LOGGER.info("🎧 [JAAM] Pipeline active. Listening to hybrid text/binary stream channel...")

    while True:
        try:
            # Enforce an internal NN-second read timeout loop to consistently check the Watchdog window
            # This prevents the system from hanging indefinitely if the remote server stays silent
            message = await asyncio.wait_for(websocket.recv(), timeout=config.SOCKET_READ_TIMEOUT_SEC)
            if isinstance(message, bytes):
                if not message: continue
                header_byte = message[0]
                config.last_heartbeat = datetime.now(config.CURRENT_TZ)

                # --- TRANSPORT LAYER FILTERING GATE ---
                # Safely skip environmental data and firmware binary OTA transmission blocks
                if header_byte in (constants.TYPE_WEATHER_BATCH, constants.TYPE_ENERGY_BATCH, constants.TYPE_RADIATION_BATCH, 
                                   constants.TYPE_FIRMWARE_UPDATE_BETA_BATCH, constants.TYPE_FIRMWARE_UPDATE_PROD_BATCH):
                    LOGGER.debug(f"🐛 [JAAM] Non-alert payload {hex(header_byte)} skipped safely.")
                    continue

                # Core operational logging for verified alert channels
                LOGGER.debug(f"🐛 [JAAM] Binary payload. Header: {hex(header_byte)} (Size: {len(message)}B)")
                LOGGER.debug(f"🐛 [JAAM] Binary payload. Message: {message}")

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
                except Exception as parse_error:
                    LOGGER.exception(f"💥 [JAAM] Internal error inside frame decoding processor: {parse_error}")
                finally:
                    # Always release the lock so the web server can serve the updated layout
                    config.cache_ready_event.set()

        except asyncio.TimeoutError:
            # The read timed out, check if the global heartbeat has crossed the NN-minute fatal limit
            minutes_since_pulse = (datetime.now(config.CURRENT_TZ) - config.last_heartbeat).total_seconds() / 60.0
            if minutes_since_pulse > config.HEALTH_FATAL_RECONNECT_MIN:
                LOGGER.warning(f"🚨 [JAAM] Watchdog: No telemetry data for {int(minutes_since_pulse)} minutes. Force-dropping stalled socket connection...")
                # Raising an exception breaks the current execution block and forces a clean reconnection lifecycle
                raise websockets.exceptions.ConnectionClosed(None, None)
            continue

async def run_provider():
    chip_id = get_dynamic_chip_id()
    LOGGER.info(f"🤖 Booting JAAM client engine. ID: {chip_id} FW: {constants.CURRENT_VERSION}")

    delay = config.PIPELINE_RECONNECT_DELAY_SEC
    while True:
        started = time.monotonic()
        try:
            # Block HTTP requests immediately on startup or when connection drops
            config.cache_ready_event.clear()

            async with websockets.connect(
                constants.URI,
                ping_interval=None
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
            LOGGER.warning(f"⚠️ [JAAM] Pipeline connection closed by server. Code: {e.code}, Reason: '{e.reason}'")

        except Exception as e:
            LOGGER.exception(f"💥 [JAAM] Connection lost or error: {e}.")

        finally:
            # Safely release HTTP threads lock if connection routine crashes or breaks
            config.cache_ready_event.set()

        # --- MANDATORY EXPONENTIAL BACKOFF WITH JITTER AND RESET LOGIC ---
        connection_duration = time.monotonic() - started
        if connection_duration > 60.0:
            # Reset backoff back to default configuration if connection survived long enough
            delay = config.PIPELINE_RECONNECT_DELAY_SEC

        # Calculate random jitter factor based on current execution delay
        calculated_delay = delay * random.uniform(0.8, 1.2)
        LOGGER.info(f"🔄 [JAAM] Reconnecting in {calculated_delay:.2f} seconds...")
        await asyncio.sleep(calculated_delay)

        # Multiply base delay for the next incremental fallback iteration if failures persist
        delay = min(delay * 2.0, 300.0)
