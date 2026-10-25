"""Alert Map Proxy Server - Web Server."""

import contextlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import config
import yaml
from bottle import request, response, route, run, sys

# Initialize module-level logger
LOGGER = logging.getLogger(__name__)


def _wait_for_cache() -> str or None:
    """
    Blocks the current HTTP worker thread until the background provider sets cache_ready_event.

    Returns an HTTP 503 error payload if the cache generation times out.
    """
    # Wait up to 10 seconds for the cache to be released by the ingestion pipeline
    if not config.cache_ready_event.wait(timeout=config.WEB_SERVER_TIMEOUT_SEC):
        response.status = 503
        return json.dumps({"status": -1, "error": "System cache is temporarily unavailable (timeout)"}, ensure_ascii=False)
    return None


@route("/")
def http_get_map_state() -> object:
    """Retrieve full application state cache metrics layer."""
    response.content_type = "application/json; charset=UTF-8"

    # Block and wait until the cache is fully ready
    timeout_response = _wait_for_cache()
    if timeout_response:
        return timeout_response

    return json.dumps(config.state_cache, ensure_ascii=False)


@route("/status/<region_id:int>")
def http_get_single_region_state(region_id: int) -> object:
    """Get summarized mapping statuses for a specific region ID parameter."""
    response.content_type = "application/json; charset=UTF-8"

    # Block and wait until the cache is fully ready
    timeout_response = _wait_for_cache()
    if timeout_response:
        return timeout_response

    target_province = None

    # Primary precise lookup (Check if ID is the FIRST element in any list)
    for province_name, ids_list in config.EXTENDED_MAPPING_MATRIX.items():
        if ids_list and ids_list[0] == region_id:
            target_province = province_name
            break

    # Secondary deep lookup (Fallback if not found as primary entity)
    if not target_province:
        for province_name, ids_list in config.EXTENDED_MAPPING_MATRIX.items():
            if region_id in ids_list:
                target_province = province_name
                break

    # Handle structural missing errors with error metadata layout
    if not target_province:
        return json.dumps({"status": -1, "error": "Region ID not mapped in system matrix"}, ensure_ascii=False)

    if "states" not in config.state_cache or target_province not in config.state_cache["states"]:
        return json.dumps({"status": -1, "error": f"State tree node for '{target_province}' uninitialized"}, ensure_ascii=False)

    alert_node = config.state_cache["states"][target_province]["alerts"]
    is_enabled = bool(alert_node.get("enabled", False))
    is_yellow = bool(alert_node.get("yellow", False))

    # Resolve dynamic status mapping (0, 1, or 2)
    numeric_status = 0 if not is_enabled else (2 if is_yellow else 1)

    # Return comprehensive state dataset response
    return json.dumps({"status": numeric_status, "region": target_province}, ensure_ascii=False)


@route("/states/<region_id:int>")
def http_get_single_region_raw_branch(region_id: int) -> object:
    """Export full dictionary tree context details for a target region block."""
    response.content_type = "application/json; charset=UTF-8"

    # Block and wait until the cache is fully ready
    timeout_response = _wait_for_cache()
    if timeout_response:
        return timeout_response

    target_province = None

    # Primary precise lookup (Check if ID is the FIRST element in any list)
    for province_name, ids_list in config.EXTENDED_MAPPING_MATRIX.items():
        if ids_list and ids_list[0] == region_id:
            target_province = province_name
            break

    # Secondary deep lookup (Fallback if not found as primary entity)
    if not target_province:
        for province_name, ids_list in config.EXTENDED_MAPPING_MATRIX.items():
            if region_id in ids_list:
                target_province = province_name
                break

    # Handle structural missing errors with clean error payload format
    if not target_province:
        return json.dumps({"status": -1, "error": "Region ID not mapped in system matrix"}, ensure_ascii=False)

    if "states" not in config.state_cache or target_province not in config.state_cache["states"]:
        return json.dumps({"status": -1, "error": f"State tree node for '{target_province}' uninitialized"}, ensure_ascii=False)

    # Create a shallow copy of the state branch to prevent state_cache mutation
    raw_region_node = dict(config.state_cache["states"][target_province])

    # Inject the flat region identity metadata key into the root layer
    raw_region_node["region"] = target_province

    return json.dumps(raw_region_node, ensure_ascii=False)


@route("/states/summary")
def http_get_multiple_regions_summary() -> object:  # noqa: C901
    """Compile custom array matrix filter map from comma-separated sequence ids."""
    response.content_type = "application/json; charset=UTF-8"

    # Block and wait until the cache is fully ready
    timeout_response = _wait_for_cache()
    if timeout_response:
        return timeout_response

    # Extract and parse 'ids' query parameter (e.g., /states/summary?ids=14,10,24,25)
    raw_ids = request.query.get("ids", "").strip()
    if not raw_ids:
        return json.dumps({"status": -1, "error": "Missing required 'ids' query parameter"}, ensure_ascii=False)

    try:
        target_ids = [int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()]
    except Exception:  # noqa: BLE001
        return json.dumps({"status": -1, "error": "Invalid format in 'ids' parameter"}, ensure_ascii=False)

    # Map provided IDs to unique active text provinces in the cache
    matched_provinces = set()
    for region_id in target_ids:
        for province_name, ids_list in config.EXTENDED_MAPPING_MATRIX.items():
            if (ids_list and ids_list[0] == region_id) or (region_id in ids_list):
                matched_provinces.add(province_name)
                break

    # If none of the passed IDs match any mapped system zones
    if not matched_provinces:
        return json.dumps({"status": -1, "error": "None of the provided IDs matched active regions"}, ensure_ascii=False)

    # Analyze operational statuses across all matched nodes using new priority hierarchy
    has_red = False
    has_yellow = False

    for province_name in matched_provinces:
        if "states" not in config.state_cache or province_name not in config.state_cache["states"]:
            continue
        alert_node = config.state_cache["states"][province_name]["alerts"]
        if bool(alert_node.get("enabled", False)):
            if bool(alert_node.get("yellow", False)):
                has_yellow = True
            else:
                has_red = True

    # Evaluate matrix priority logic rules
    # - 1: If ANY checked region has a primary red alert active
    # - 2: If ANY checked region has a yellow alert active AND NO regions are red
    # - 0: If NO checked regions have any alerts active (completely clear)
    summary_status = 1 if has_red else (2 if has_yellow else 0)

    return json.dumps({"status": summary_status, "checked_regions": list(matched_provinces)}, ensure_ascii=False)


@route("/states/flat")
def http_get_all_regions_flat_summary() -> object:
    """Provide minimal fast numeric evaluation status table blueprint stream."""
    response.content_type = "application/json; charset=UTF-8"

    # Block and wait until the cache is fully ready
    timeout_response = _wait_for_cache()
    if timeout_response:
        return timeout_response

    flat_matrix_status = {}

    # Loop through every pre-defined zone in the mapping matrix
    for province_name in config.EXTENDED_MAPPING_MATRIX:
        # Safety fallback for uninitialized cache records
        if "states" not in config.state_cache or province_name not in config.state_cache["states"]:
            flat_matrix_status[province_name] = 0
            continue

        alert_node = config.state_cache["states"][province_name]["alerts"]
        is_enabled = bool(alert_node.get("enabled", False))
        is_yellow = bool(alert_node.get("yellow", False))

        # Evaluate threat level numeric mapping logic for the region
        # - 0: Safe (No alerts active)
        # - 1: Red Air Alert (Primary siren active, yellow is false)
        # - 2: Yellow Air Alert (Low-level/silent warning active)
        flat_matrix_status[province_name] = 0 if not is_enabled else (2 if is_yellow else 1)

    # Return pure, unmapped flat key-value dictionary schema
    return json.dumps(flat_matrix_status, ensure_ascii=False)


@route("/states/packed")
def http_get_all_regions_packed_bitmap() -> object:
    """Synthesize aggregated integer statuses combining operational metrics layers."""
    response.content_type = "application/json; charset=UTF-8"

    # Block and wait until the cache is fully ready
    timeout_response = _wait_for_cache()
    if timeout_response:
        return timeout_response

    # Parse the sliding threat timeout window parameter (in minutes)
    raw_timeout = request.query.get("timeout", "").strip()
    timeout_minutes = int(raw_timeout) if raw_timeout.isdigit() else None

    # Get current precise time object in Europe/Kyiv zone for exact interval subtraction
    kyiv_now = datetime.now(config.CURRENT_TZ)
    packed_matrix_status = {}

    # Loop through every pre-defined zone in the mapping matrix
    for province_name in config.EXTENDED_MAPPING_MATRIX:
        if "states" not in config.state_cache or province_name not in config.state_cache["states"]:
            packed_matrix_status[province_name] = 0
            continue

        region_data = config.state_cache["states"][province_name]
        threat_node = region_data["threats"]
        is_enabled = bool(region_data["alerts"].get("enabled", False))
        is_yellow = bool(region_data["alerts"].get("yellow", False))

        # Strict mathematical time interval validation
        # Ensures threat freshness falls strictly within the specified minute window
        threats_expired = False
        raw_updated = threat_node.get("updated")
        if timeout_minutes is not None and raw_updated:
            try:
                # If threat record age is greater than requested timeout, it expires
                if (kyiv_now - datetime.fromisoformat(raw_updated)).total_seconds() > (timeout_minutes * 60):
                    threats_expired = True
            except Exception:  # noqa: BLE001
                # Force expiration fallback if timestamp data gets corrupted
                threats_expired = True

        # fmt: off
        # Calculate the dynamic tactical threat bitmask layer if not expired
        tactical_bitmask = 0
        if not threats_expired:
            threat_mapping = {
                "artillery": 1,   # 2
                "urban": 2,       # 4
                "chemical": 3,    # 8
                "nuclear": 4,     # 16
                "drones": 5,      # 32
                "missiles": 6,    # 64
                "kabs": 7,        # 128
                "ballistic": 8,   # 256
                "explosions": 9,  # 512
                "recon": 10,      # 1024
            }
            for threat_key, bit_shift in threat_mapping.items():
                if bool(threat_node.get(threat_key, False)):
                    tactical_bitmask |= (1 << bit_shift)
        # fmt: on

        # Apply the baseline mathematical compression math logic
        final_value = tactical_bitmask if not is_enabled else ((20000 + tactical_bitmask) if is_yellow else (10000 + tactical_bitmask))
        packed_matrix_status[province_name] = final_value

    # Return compressed global packed bitmap array response
    return json.dumps(packed_matrix_status, ensure_ascii=False)


@route("/states/map")
def http_get_custom_yaml_mapped_states() -> object:  # noqa: C901, PLR0912
    """Render client-tailored telemetry map metrics based on static config assets."""
    response.content_type = "application/json; charset=UTF-8"

    # Block and wait until the cache is fully ready
    timeout_response = _wait_for_cache()
    if timeout_response:
        return timeout_response

    # Parse the sliding threat timeout window parameter (in minutes)
    raw_timeout = request.query.get("timeout", "").strip()
    timeout_minutes = int(raw_timeout) if raw_timeout.isdigit() else None
    kyiv_now = datetime.now(config.CURRENT_TZ)

    # Verify if the map.yaml configuration file exists
    yaml_path = Path(config.YAML_CONFIG_PATH)
    if not yaml_path.exists():
        return json.dumps({"status": -1, "error": "Configuration file not found"}, ensure_ascii=False)

    # Safe parse the YAML matrix payload structure
    try:
        with yaml_path.open(encoding="utf-8") as f:
            user_mapping = yaml.safe_load(f)
    except Exception as e:  # noqa: BLE001
        return json.dumps({"status": -1, "error": str(e)}, ensure_ascii=False)

    flat_custom_status = {}

    # Iterate over the user's custom structural definitions
    for province_name, custom_ids_list in user_mapping.items():
        if not isinstance(custom_ids_list, list):
            continue

        # Extract operational alert and threat data from global state cache
        alert_node = config.state_cache["states"].get(province_name, {}).get("alerts") if "states" in config.state_cache else None
        threat_node = config.state_cache["states"].get(province_name, {}).get("threats") if "states" in config.state_cache else None

        is_enabled = bool(alert_node.get("enabled", False)) if alert_node else False
        is_yellow = bool(alert_node.get("yellow", False)) if alert_node else False

        # Validate if there is any active threat STRICTLY when timeout parameter is provided
        has_active_threat = False
        if timeout_minutes is not None and threat_node:
            # Check if any boolean threat flag is currently True
            has_any_flag = any(
                bool(threat_node.get(k, False))
                for k in ["artillery", "urban", "chemical", "nuclear", "drones", "missiles", "kabs", "ballistic", "explosions", "recon"]
            )

            if has_any_flag and threat_node.get("updated"):
                with contextlib.suppress(Exception):
                    if (kyiv_now - datetime.fromisoformat(threat_node.get("updated"))).total_seconds() <= (timeout_minutes * 60):
                        has_active_threat = True

        # Calculate the dynamic alert level status code factor (0, 1, 2, 3, 4)
        # - 0: Safe (No alert)
        # - 1: Red Alert siren active (Returned by default if timeout parameter is missing or threat expired)
        # - 2: Yellow Alert status active (Returned by default if timeout parameter is missing or threat expired)
        # - 3: Red Alert siren active + FRESH tactical threat detected STRICTLY within timeout window
        # - 4: Yellow Alert status active + FRESH tactical threat detected STRICTLY within timeout window
        if not is_enabled:
            numeric_status = 0
        elif not is_yellow:
            numeric_status = 3 if has_active_threat else 1
        else:
            numeric_status = 4 if has_active_threat else 2

        # Distribute the calculated status to all bound custom IDs
        for custom_id in custom_ids_list:
            try:
                flat_custom_status[int(custom_id)] = numeric_status
            except (ValueError, TypeError):
                continue

    # Return flat raw integer-mapped layout JSON stream response
    return json.dumps(flat_custom_status, ensure_ascii=False)


@route("/health")
def http_get_proxy_health_status() -> object:
    """Evaluate pipeline freshness thresholds and report system telemetry state."""
    response.content_type = "application/json; charset=UTF-8"

    kyiv_now = datetime.now(config.CURRENT_TZ)
    time_difference = kyiv_now - config.last_heartbeat
    minutes_stalled = time_difference.total_seconds() / 60.0

    # 4-Tier Health Ecosystem Priority Rules:
    # - "online": Less than or equal to 5 minutes since the last valid byte transmission
    # - "idle": Greater than 5 minutes but less than or equal to 10 minutes
    # - "critical": Greater than 10 minutes but less than or equal to 15 minutes
    # - "offline": Greater than 15 minutes (Socket dropped or Watchdog termination in progress)
    if minutes_stalled <= config.HEALTH_ONLINE_THRESHOLD_MIN:
        health_status = "online"
    elif minutes_stalled <= config.HEALTH_IDLE_THRESHOLD_MIN:
        health_status = "idle"
    elif minutes_stalled <= config.HEALTH_CRITICAL_THRESHOLD_MIN:
        health_status = "critical"
    else:
        health_status = "offline"

    return json.dumps(
        {
            "status": health_status,
            "last_heartbeat": config.last_heartbeat.isoformat(),
            "seconds_since_last_packet": int(time_difference.total_seconds()),
        },
        ensure_ascii=False,
    )


@route("/ping")
def http_ping() -> object:
    """Handle structural ping diagnostics check."""
    return {"status": "online", "servertime": time.time()}


def run_http_server() -> None:
    """Deploy and bind WSGI application container layer to selected network nodes."""
    try:
        run(
            host=config.HTTP_SERVER_HOST,
            port=config.HTTP_SERVER_PORT,
            server=config.HTTP_SERVER_ENGINE,
            quiet=config.HTTP_SERVER_QUIET_MODE,
        )
    except Exception:
        LOGGER.exception("❌ Unexpected crash inside HTTP thread deployment:")
        sys.exit(1)
