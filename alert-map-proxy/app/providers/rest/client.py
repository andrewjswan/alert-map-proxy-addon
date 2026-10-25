import asyncio
import config
import gzip
import json
import logging
import urllib.request
from datetime import datetime, timedelta
from . import constants
from . import processor

# Initialize module-level logger dynamically based on the package namespace
LOGGER = logging.getLogger(__name__)

def fetch_http_sync(url_target):
    """Performs block-free standard synchronized network descriptor lookups using full Chrome specs."""
    headers = {
        "User-Agent": constants.USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }

    req = urllib.request.Request(url_target, headers=headers)

    with urllib.request.urlopen(req, timeout=10) as response:
        raw_bytes = response.read()

        # Dynamic transport layer decompression wrapper gate
        if response.info().get("Content-Encoding") == "gzip":
            try:
                raw_bytes = gzip.decompress(raw_bytes)
            except Exception as decomp_err:
                LOGGER.error("❌ [REST] Failed to decompress incoming gzip stream payload: %s", decomp_err)
                return ""

        return raw_bytes.decode("utf-8")

async def run_provider():
    """Main lifecycle loop handling fallback multi-source polling based on 5-minute data freshness."""
    LOGGER.info("🤖 Booting Multi-Source REST Engine with Dynamic Fallback Strategy (%d-min freshness threshold)...", constants.MAX_CACHE_AGE_MINUTES)
    loop = asyncio.get_running_loop()

    while True:
        elected_payload = None
        elected_url_source = ""

        # --- SEQUENTIAL MULTI-SOURCE POLLING WITH FIRST-VALID FALLBACK ---
        for url_target in constants.URI_LIST:
            try:
                # Offload blocking network descriptor call to internal pool executor
                raw_json = await loop.run_in_executor(None, fetch_http_sync, url_target)

                if not raw_json or not raw_json.strip():
                    LOGGER.debug("⚠️ Endpoint '%s' returned an empty response, skipping to next provider.", url_target)
                    continue

                payload = json.loads(raw_json)

                # Dynamic schema and cache validation check
                if isinstance(payload, dict) and "cachedat" in payload:
                    raw_cache_str = payload.get("cachedat", "")

                    try:
                        # Parse standard timestamp string directly (e.g., '2026-10-15 23:04:55')
                        current_dt = datetime.strptime(raw_cache_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=config.CURRENT_TZ)

                        # Calculate payload data age frame
                        data_age = datetime.now(config.CURRENT_TZ) - current_dt

                        # CRITICAL FRESHNESS RULE: Accept immediately if data is within the configured time limit
                        if data_age <= timedelta(minutes=constants.MAX_CACHE_AGE_MINUTES):
                            elected_payload = payload
                            elected_url_source = url_target
                            # Break sequential polling loop early since a valid primary leader is found
                            break
                        else:
                            LOGGER.debug(
                                "⏳ Data from '%s' is stale (age: %s). Proceeding to fallback endpoint.", 
                                url_target, data_age
                            )

                    except ValueError:
                        # Fallback parsing strategy if timestamp format gets malformed by upstream proxy wrappers
                        elected_payload = payload
                        elected_url_source = url_target
                        break

            except Exception as source_fault:
                LOGGER.debug("🐛 [REST] Endpoint '%s' temporarily unreachable: %s", url_target, source_fault)

            # Inter-request delay throttle constraint to prevent CDN rate limiting blocks during fallback routine
            await asyncio.sleep(constants.POLL_INTERVAL_SEC)

        # --- DISPATCH THE ELECTED FRESH BUFFER FRAME ---
        if elected_payload:
            config.last_heartbeat = datetime.now(config.CURRENT_TZ)
            raw_data_block = elected_payload.get("raw")

            LOGGER.debug("🎯 Electing source [%s] as leader. Cache timestamp: %s", elected_url_source, elected_payload.get("cachedat"))

            try:
                # Lock only when we actually have fresh data to process
                config.cache_ready_event.clear()

                if isinstance(raw_data_block, list):
                    processor.process_rest_update({"alerts": raw_data_block})
                elif isinstance(raw_data_block, dict):
                    processor.process_rest_update({"alerts": raw_data_block})
                else:
                    processor.process_rest_update(elected_payload)
            except Exception as update_err:
                LOGGER.error("❌ [REST] Ingestion pipeline failed during cache processing: %s", update_err)
        else:
            LOGGER.error(
                "💥 [REST] Critical connectivity failure: All endpoints are offline or serving stale data (> %d min).",
                constants.MAX_CACHE_AGE_MINUTES
            )

        # Safely release the HTTP threads in any scenario (success or failure)
        config.cache_ready_event.set()

        # Global loop delay constraint before initiating next master fallback execution sweep
        await asyncio.sleep(constants.POLL_INTERVAL_SEC)
