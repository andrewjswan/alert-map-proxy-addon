import asyncio
import json
import websockets
from datetime import datetime
import config
import logging
from . import constants
from . import processor

# Initialize module-level logger
LOGGER = logging.getLogger(__name__)

async def receive_messages(websocket):
    """Processes incoming frame strings from Neptun pipeline channel."""
    while True:
        try:
            # Enforce continuous verification via socket timeout window limits
            message = await asyncio.wait_for(websocket.recv(), timeout=config.SOCKET_READ_TIMEOUT_SEC)
            config.last_heartbeat = datetime.now(config.CURRENT_TZ)
            
            try:
                envelope = json.loads(message)
                event_type = envelope.get("type")
                data = envelope.get("data")
                
                # Lock the HTTP worker threads before entering the processor routing layer
                config.cache_ready_event.clear()

                # Dynamic stream state dispatcher matching message specifications
                if event_type == "snapshot":
                    if isinstance(data, dict):
                        processor.handle_neptun_snapshot(data)
                elif event_type == "upsert":
                    if isinstance(data, dict):
                        processor.handle_neptun_upsert(data)
                elif event_type == "remove":
                    if isinstance(data, dict):
                        processor.handle_neptun_remove(data)
                elif event_type == "alerts":
                    if isinstance(data, dict):
                        processor.process_neptun_alerts(data)
                elif event_type == "heartbeat":
                    LOGGER.debug("🔱 [NEPTUN] Keep-alive heartbeat packet acknowledged.")
                else:
                    LOGGER.debug(f"🐛 [NEPTUN] Received unhandled event type: '{event_type}'")
                    
            except json.JSONDecodeError:
                LOGGER.exception("⚠️ [NEPTUN] Failed to decode incoming JSON payload block.")
            except Exception as parse_error:
                LOGGER.exception(f"💥 [NEPTUN] Internal error inside frame decoding processor: {parse_error}")
            finally:
                # Safely release the HTTP threads lock after processing the message frame
                config.cache_ready_event.set()

        except asyncio.TimeoutError:
            minutes_since_pulse = (datetime.now(config.CURRENT_TZ) - config.last_heartbeat).total_seconds() / 60.0
            if minutes_since_pulse > config.HEALTH_FATAL_RECONNECT_MIN:
                LOGGER.warning("🚨 [NEPTUN] Watchdog: Neptun stream stalled. Dropping connection architecture line...")
                raise websockets.exceptions.ConnectionClosed(None, None)
            continue

async def run_provider():
    LOGGER.info("🤖 Booting NEPTUN client core. Handshake configuration skipped.")
    
    while True:
        try:
            # Block HTTP requests immediately when connection drops or starts up
            config.cache_ready_event.clear()

            async with websockets.connect(constants.URI) as websocket:
                LOGGER.info("✅ [NEPTUN] Core pipeline linked into remote NEPTUN server architecture stream!")
                config.last_heartbeat = datetime.now(config.CURRENT_TZ)
                
                processor.reset_neptun_cache()
                LOGGER.info("🚀 [NEPTUN] Pipeline online for NEPTUN. Streaming live telemetry data maps...")

                await receive_messages(websocket)

        except websockets.exceptions.ConnectionClosed as e:
            LOGGER.warning(f"⚠️ [NEPTUN] Pipeline connection closed by server. Code: {e.code}, Reason: '{e.reason}'")

        except Exception as e:
            LOGGER.exception(f"💥 [NEPTUN] Connection lost or error: {e}.")

        finally:
            # Ensure the lock is released if we break out or encounter a fatal failure before loop repeats
            config.cache_ready_event.set()
 
        LOGGER.info(f"🔄 [NEPTUN] Reconnecting in {config.PIPELINE_RECONNECT_DELAY_SEC} seconds...")
        await asyncio.sleep(config.PIPELINE_RECONNECT_DELAY_SEC)
