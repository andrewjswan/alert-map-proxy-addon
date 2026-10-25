"""Alert Map Proxy Server - JAAM Provider - Processor."""

import logging
import struct
from datetime import datetime

import config

from . import constants

# Initialize module-level logger
LOGGER = logging.getLogger(__name__)

# Persistent regional storage independent of state_cache to avoid pollution
region_cache = {}


def reset_jaam_cache() -> None:
    """Reset all metrics inside high-level state_cache back to pristine operational defaults."""
    for region_name in config.EXTENDED_MAPPING_MATRIX:
        states = config.state_cache["states"][region_name]
        states["alerts"]["enabled"] = False
        states["alerts"]["yellow"] = False
        states["alerts"]["updated"] = None
        for key in states["threats"]:
            if key == "updated":
                states["threats"][key] = None
            else:
                states["threats"][key] = False


def process_jaam_batch(payload_bytes: bytes, offset: int, notify: bool = False) -> None:  # noqa: C901, FBT001, FBT002
    """
    Universally parse 4-byte structural streaming pairs.

    This function extracts information from 0xA1 and 0xA2 server streams using an isolated global region cache.
    """
    global region_cache  # noqa: PLW0602

    record_size = 4
    kyiv_now = datetime.now(config.CURRENT_TZ).isoformat()

    # Tracking matrix for provinces whose child IDs appeared in the packet
    impacted_provinces = set()

    # --- LAYER 1: DEMUX LOGIC INTO INDEPENDENT GLOBAL REGION CACHE ---
    while offset + record_size <= len(payload_bytes):
        region_id, flags16 = struct.unpack_from("<HH", payload_bytes, offset)
        offset += record_size

        if not notify:
            # 0xA1: Overwrite the telemetry state snapshot for this exact node
            region_cache[region_id] = flags16
        else:
            # 0xA2: Tactical layer update, append active bits with bitwise OR
            current_flags = region_cache.get(region_id, 0)
            region_cache[region_id] = current_flags | flags16

        # Detect mapping intersections based on aggregation mode constraint
        for province_name, ids_list in config.EXTENDED_MAPPING_MATRIX.items():
            if config.USE_AGGREGATION:
                # Standard mode: Scan across all IDs in the province block
                if region_id in ids_list:
                    impacted_provinces.add(province_name)
            # Strict mode: Match ONLY against the primary ID (index 0) of the list
            elif ids_list and region_id == ids_list[0]:
                impacted_provinces.add(province_name)

    # --- LAYER 2: MULTI-MATCHING RE-AGGREGATION ON FINAL STATE TREE ---
    for province_name in impacted_provinces:
        ids_list = config.EXTENDED_MAPPING_MATRIX[province_name]
        states = config.state_cache["states"][province_name]

        # Calculate consolidated mask depending on the loaded environment branch
        aggregated_flags = 0
        if config.USE_AGGREGATION:
            # Merge individual region snapshots using absolute bitwise OR summation
            for r_id in ids_list:
                aggregated_flags |= region_cache.get(r_id, 0)
        # Fallback to the primary ID only (index 0), ignoring other elements
        elif ids_list:
            aggregated_flags = region_cache.get(ids_list[0], 0)

        # fmt: off

        # --- OFFICIAL AIR ALERT VALIDATION (ONLY FOR 0xA1) ---
        if not notify:
            # Extract air alert bits from consolidated mask
            has_low_air  = bool(aggregated_flags & constants.BIT_ALERT_LOW)
            has_high_air = bool(aggregated_flags & constants.BIT_ALERT_HIGH)

            states["alerts"]["enabled"] = has_low_air or has_high_air
            states["alerts"]["yellow"]  = has_low_air and not has_high_air
            states["alerts"]["updated"] = kyiv_now

        # --- EXTENDED THREAT TREE RECORDING ---
        states["threats"]["artillery"]  = bool(aggregated_flags & constants.BIT_ARTILLERY)
        states["threats"]["urban"]      = bool(aggregated_flags & constants.BIT_URBAN)
        states["threats"]["chemical"]   = bool(aggregated_flags & constants.BIT_CHEMICAL)
        states["threats"]["nuclear"]    = bool(aggregated_flags & constants.BIT_NUCLEAR)
        states["threats"]["drones"]     = bool(aggregated_flags & constants.BIT_DRONES)
        states["threats"]["missiles"]   = bool(aggregated_flags & constants.BIT_MISSILES)
        states["threats"]["kabs"]       = bool(aggregated_flags & constants.BIT_KABS)
        states["threats"]["ballistic"]  = bool(aggregated_flags & constants.BIT_BALLISTIC)
        states["threats"]["explosions"] = bool(aggregated_flags & constants.BIT_EXPLOSION)
        states["threats"]["recon"]      = bool(aggregated_flags & constants.BIT_RECON_DRONES)
        states["threats"]["updated"]    = kyiv_now

        # fmt: on
