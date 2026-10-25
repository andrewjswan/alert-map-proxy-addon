"""Alert Map Proxy Server - Neptun Provider - Processor."""

import logging
from datetime import datetime

import config

# Initialize module-level logger
LOGGER = logging.getLogger(__name__)

# In-memory registry tracking live objects by their strict unique IDs
# Layout schema: { "trk_00209788": {"type": "drones", "region_key": "Чернігівська обл."}, ... }
active_threats = {}

# Map Neptun threat identifier tokens directly to hardware-supported state tree variables
THREAT_TYPE_MAPPING = {
    "uav": "drones",
    "recon": "recon",
    "missile": "missiles",
    "mig31k": "missiles",
    "ballistic": "ballistic",
    "kab": "kabs",
}


def parse_neptun_time(time_str: str | None) -> str | None:
    """Parse ISO timestamp from UTC and converts it to Europe/Kyiv timezone."""
    if not time_str or time_str == "N/A":
        return None
    try:
        clean_str = time_str.replace("Z", "+00:00")
        if "." in clean_str:
            base, tz = clean_str.split("+")
            main, ms = base.split(".")
            clean_str = f"{main}.{ms[:6]}+{tz}"
        return datetime.fromisoformat(clean_str).astimezone(config.CURRENT_TZ)
    except ValueError:
        return None


def normalize_oblast_name(name_str: str | None) -> str | None:
    """Translate Neptun oblast naming convention into EXTENDED_MAPPING_MATRIX keys."""
    if not name_str:
        return None

    stripped = name_str.strip()

    # Map strict special territory exceptions
    if "Крим" in stripped or "АВТОНОМНА" in stripped.upper():
        return "АР Крим"
    if stripped in {"м. Київ", "Київ"}:
        return "м. Київ"

    # Standard transformation: 'Київська область' -> 'Київська обл.'
    if stripped.endswith("область"):
        return stripped.replace("область", "обл.")

    return stripped


def get_target_matrix_regions(normalized_name: str | None) -> list[str]:
    """Map a single normalized oblast name to a list of target matrix region keys, duplicating for cities."""
    if not normalized_name or normalized_name not in config.EXTENDED_MAPPING_MATRIX:
        return []

    # Kyiv is already handled as a strict standalone entity, do not duplicate
    if normalized_name in ("м. Київ", "Київська обл.", "АР Крим"):
        return [normalized_name]

    # Establish strict programmatic links between oblast keys and their corresponding main city keys
    city_mapping = {
        "Черкаська обл.": "м. Черкаси",
        "Вінницька обл.": "м. Вінниця",
        "Волинська обл.": "м. Луцьк",
        "Дніпропетровська обл.": "м. Дніпро",
        "Житомирська обл.": "м. Житомир",
        "Закарпатська обл.": "м. Ужгород",
        "Запорізька обл.": "м. Запоріжжя",
        "Івано-Франківська обл.": "м. Івано-Франківськ",
        "Кіровоградська обл.": "м. Кропивницький",
        "Львівська обл.": "м. Львів",
        "Миколаївська обл.": "м. Миколаїв",
        "Одеська обл.": "м. Одеса",
        "Полтавська обл.": "м. Полтава",
        "Рівненська обл.": "м. Рівне",
        "Сумська обл.": "м. Суми",
        "Тернопільська обл.": "м. Тернопіль",
        "Харківська обл.": "м. Харків",
        "Херсонська обл.": "м. Херсон",
        "Хмельницька обл.": "м. Хмельницький",
        "Чернівецька обл.": "м. Чернівці",
        "Чернігівська обл.": "м. Чернігів",
    }

    # If the region is a standard oblast, return both the oblast and its city token
    if normalized_name in city_mapping:
        return [normalized_name, city_mapping[normalized_name]]

    return [normalized_name]


def reset_neptun_cache() -> None:
    """Clean reset pattern tailored for Neptun system mapping structure."""
    global active_threats  # noqa: PLW0602
    active_threats.clear()

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


def process_neptun_alerts(data_dict: dict) -> None:  # noqa: C901, PLR0912
    """Handle parsing of secondary air raid alerts array schemas."""
    kyiv_now = datetime.now(config.CURRENT_TZ).isoformat()
    packet_registry = {
        region_key: {
            "has_red": False,
            "has_yellow": False,
            "oblast_override": None,
            "latest_dt": None,
        }
        for region_key in config.EXTENDED_MAPPING_MATRIX
    }

    # --- PHASE 1: PARSE INTERMEDIATE THREAT LEVELS FROM RAIONS ---
    for raion in data_dict.get("raions", []):
        raw_oblast = raion.get("oblast")
        norm_name = normalize_oblast_name(raw_oblast)

        # Resolve all bound matrix keys (oblast + target city if applicable)
        for region_key in get_target_matrix_regions(norm_name):
            level = str(raion.get("level", "")).upper()
            dt_object = parse_neptun_time(raion.get("since"))

            if level == "RED":
                packet_registry[region_key]["has_red"] = True
            elif level == "YELLOW":
                packet_registry[region_key]["has_yellow"] = True

            current_latest = packet_registry[region_key]["latest_dt"]
            if dt_object and (not current_latest or dt_object > current_latest):
                packet_registry[region_key]["latest_dt"] = dt_object

    # --- PHASE 2: PARSE HIGH LEVEL OVERRIDES FROM OBLASTS ---
    for obl_item in data_dict.get("oblasts", []):
        raw_oblast = obl_item.get("oblast")
        norm_name = normalize_oblast_name(raw_oblast)

        for region_key in get_target_matrix_regions(norm_name):
            level = str(obl_item.get("level", "")).upper()
            dt_object = parse_neptun_time(obl_item.get("since"))

            if level in ("RED", "YELLOW"):
                packet_registry[region_key]["oblast_override"] = level

            current_latest = packet_registry[region_key]["latest_dt"]
            if dt_object and (not current_latest or dt_object > current_latest):
                packet_registry[region_key]["latest_dt"] = dt_object

    # --- PHASE 3: COMMIT TO STATE CACHE WITH UPDATE TIMESTAMP RETENTION ---
    for region_key, metrics in packet_registry.items():
        states = config.state_cache["states"][region_key]

        was_enabled = bool(states["alerts"]["enabled"])
        final_enabled = False
        final_yellow = False
        override = metrics["oblast_override"]

        if override:
            final_enabled = True
            final_yellow = override == "YELLOW"
        elif metrics["has_red"]:
            final_enabled = True
            final_yellow = False
        elif metrics["has_yellow"]:
            final_enabled = True
            final_yellow = True

        states["alerts"]["enabled"] = final_enabled
        states["alerts"]["yellow"] = final_yellow

        if final_enabled:
            if metrics["latest_dt"]:
                states["alerts"]["updated"] = metrics["latest_dt"].isoformat()
            else:
                states["alerts"]["updated"] = kyiv_now
        elif was_enabled:
            states["alerts"]["updated"] = kyiv_now

    config.state_cache["updated"] = kyiv_now

    LOGGER.debug("⚡ [NEPTUN] Memory Sync: Cache updated successfully at %s", kyiv_now)


def recalculate_region_threats(region_key: str, kyiv_now_str: str, event_type: str) -> None:
    """Scan all live objects within the registry to update threat vectors for a specific zone."""
    states = config.state_cache["states"][region_key]
    threat_node = states["threats"]

    # Track the previous summary state before parsing new modifications
    was_threatened = any(threat_node[k] for k in ["drones", "recon", "missiles", "ballistic", "kabs"])

    # Initialize all target parameters to False before execution
    for key in ["drones", "recon", "missiles", "ballistic", "kabs"]:
        threat_node[key] = False

    has_any_threat = False

    # Iterate over every active tracked object in memory matching the zone scope
    for threat_meta in active_threats.values():
        if region_key in threat_meta["region_keys"]:
            target_field = threat_meta["type"]
            threat_node[target_field] = True
            has_any_threat = True

    # --- DYNAMIC TIMESTAMP UPDATE LOGIC MATCHING OPERATIONAL ENVIRONMENT RULES ---
    if has_any_threat:
        if not was_threatened or event_type in ("upsert", "snapshot"):
            threat_node["updated"] = kyiv_now_str
    elif was_threatened:
        threat_node["updated"] = kyiv_now_str


def process_single_threat_upsert(threat_obj: dict, kyiv_now_str: str) -> list[str]:  # noqa: ARG001
    """Extract structural telemetry data from an individual threat model."""
    global active_threats  # noqa: PLW0602

    threat_id = threat_obj.get("id")
    raw_type = threat_obj.get("type", "").lower()
    raw_region = threat_obj.get("region")

    if not threat_id or raw_type == "unknown":
        return []  # Safely ignore invalid models or explicitly rejected unknown variables

    mapped_type = THREAT_TYPE_MAPPING.get(raw_type)
    if not mapped_type:
        return []  # Skip unsupported platform fields

    norm_name = normalize_oblast_name(raw_region)
    target_regions = get_target_matrix_regions(norm_name)

    if not target_regions:
        return []

    # Append or update registry item with strict sub-key mapping layout support
    active_threats[threat_id] = {
        "type": mapped_type,
        "region_keys": target_regions,  # Store multiple bound regions for target tracking lookups
    }

    return target_regions


def handle_neptun_snapshot(data_dict: dict) -> None:
    """Process bulk array initialization block received upon pipeline socket binding link."""
    global active_threats  # noqa: PLW0602
    active_threats.clear()

    kyiv_now = datetime.now(config.CURRENT_TZ).isoformat()

    for threat_obj in data_dict.get("threats", []):
        process_single_threat_upsert(threat_obj, kyiv_now)

    # Trigger batch threat map updates across all system zones with strict event parsing
    for r_key in config.EXTENDED_MAPPING_MATRIX:
        recalculate_region_threats(r_key, kyiv_now, "snapshot")

    config.state_cache["updated"] = kyiv_now
    LOGGER.info("⚡ [NEPTUN] Snapshot: Synced %d active object tracks across regions.", len(active_threats))


def handle_neptun_upsert(data_dict: dict) -> None:
    """Process creation or dynamic movement change parameters of a single track."""
    kyiv_now = datetime.now(config.CURRENT_TZ).isoformat()
    target_regions = process_single_threat_upsert(data_dict, kyiv_now)

    if target_regions:
        for region_key in target_regions:
            recalculate_region_threats(region_key, kyiv_now, "upsert")
        config.state_cache["updated"] = kyiv_now


def handle_neptun_remove(data_dict: dict) -> None:
    """Remove a dissolved or expired object tracking index node from active memory maps."""
    global active_threats  # noqa: PLW0602
    threat_id = data_dict.get("id")

    if threat_id and threat_id in active_threats:
        kyiv_now = datetime.now(config.CURRENT_TZ).isoformat()
        target_regions = active_threats[threat_id]["region_keys"]

        # Purge key row element from memory map registry
        del active_threats[threat_id]

        # Trigger state change check execution for all zones where the object dropped
        for region_key in target_regions:
            recalculate_region_threats(region_key, kyiv_now, "remove")

        config.state_cache["updated"] = kyiv_now
