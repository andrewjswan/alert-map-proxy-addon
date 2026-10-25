"""Alert Map Proxy Server - REST Provider - Processor."""

import logging
from datetime import datetime

import config

# Initialize module-level logger dynamically based on the package namespace
LOGGER = logging.getLogger(__name__)


def parse_iso_time(time_str: str | None) -> str | None:
    """Parse standard ISO timestamps directly into Europe/Kyiv zone."""
    if not time_str:
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


def normalize_name(name_str: str | None) -> str | None:
    """Standardize text string naming variations across multiple external API formats."""
    if not name_str:
        return None
    stripped = name_str.strip()
    if "Крим" in stripped or "АРК" in stripped:
        return "АР Крим"
    if stripped.startswith("місто "):
        return stripped.replace("місто ", "м. ")
    if stripped.startswith("Місто"):
        return stripped.replace("Місто ", "м. ")
    if stripped.endswith("область"):
        return stripped.replace("область", "обл.")
    return stripped


def get_target_matrix_regions(region_name: str | None, region_type: str | None) -> list[str]:  # noqa: ARG001, PLR0911
    """Map custom provider names and structural region types to internal matrix keys."""
    if not region_name:
        return []

    # Standardize name layout mapping keys
    norm_name = normalize_name(region_name)
    if norm_name in ("АР Крим"):
        return [norm_name]

    # Strictly isolates city nodes by detecting "м. " prefix
    is_city = norm_name.startswith("м. ")
    if is_city:
        # Clean prefix markers safely
        clean_city = norm_name.replace("м. ", "").strip()

        # Truncate anything following the " та " separator to isolate the core city name
        if " та " in clean_city:
            clean_city = clean_city.split(" та ")[0].strip()

        # Re-attach standard system matrix prefix layout token
        matrix_city_key = f"м. {clean_city}"

        # Verify directly inside the main mapping matrix configuration keys
        if matrix_city_key in config.EXTENDED_MAPPING_MATRIX:
            return [matrix_city_key]

        # If the standalone city is not defined as an independent matrix node, drop it safely
        return []

    # fmt: off
    # Complete strict relational district boundaries registry map
    district_to_oblast_map = {
        # Рівненська
        "Рівненський": "Рівненська обл.", "Вараський": "Рівненська обл.", "Сарненський": "Рівненська обл.", "Дубенський": "Рівненська обл.",
        # Харківська
        "Чугуївський": "Харківська обл.", "Харківський": "Харківська обл.", "Лозівський": "Харківська обл.", "Богодухівський": "Харківська обл.", "Красноградський": "Харківська обл.", "Куп'янський": "Харківська обл.", "Ізюмський": "Харківська обл.", "Берестинський": "Харківська обл.",  # noqa: E501
        # Донецька
        "Покровський": "Донецька обл.", "Краматорський": "Донецька обл.", "Кальміуський": "Донецька обл.", "Волноваський": "Донецька обл.", "Маріупольський": "Донецька обл.", "Бахмутський": "Донецька обл.", "Донецький": "Донецька обл.", "Горлівський": "Донецька обл.",  # noqa: E501
        # Запорізька
        "Запорізький": "Запорізька обл.", "Мелітопольський": "Запорізька обл.", "Пологівський": "Запорізька обл.", "Василівський": "Запорізька обл.", "Бердянський": "Запорізька обл.",  # noqa: E501
        # Сумська
        "Шосткинський": "Сумська обл.", "Сумський": "Сумська обл.", "Охтирський": "Сумська обл.", "Конотопський": "Сумська обл.", "Роменський": "Сумська обл.",  # noqa: E501
        # Чернігівська
        "Корюківський": "Чернігівська обл.", "Ніжинський": "Чернігівська обл.", "Чернігівський": "Чернігівська обл.", "Новгород-Сіверський": "Чернігівська обл.", "Прилуцький": "Чернігівська обл.",  # noqa: E501
        # Київська
        "Бориспільський": "Київська обл.", "Броварський": "Київська обл.", "Фастівський": "Київська обл.", "Бучанський": "Київська обл.", "Білоцерківський": "Київська обл.", "Обухівський": "Київська обл.", "Вишгородський": "Київська обл.",  # noqa: E501
        # Полтавська
        "Полтавський": "Полтавська обл.", "Кременчуцький": "Полтавська обл.", "Миргородський": "Полтавська обл.", "Лубенський": "Полтавська обл.",
        # Вінницька
        "Тульчинський": "Вінницька обл.", "Гайсинський": "Вінницька обл.", "Жмеринський": "Вінницька обл.", "Вінницький": "Вінницька обл.", "Хмільницький": "Вінницька обл.", "Могилів-Подільський": "Вінницька обл.",  # noqa: E501
        # Черкаська
        "Золотоніський": "Черкаська обл.", "Черкаський": "Черкаська обл.", "Звенигородський": "Черкаська обл.", "Уманський": "Черкаська обл.",
        # Миколаївська
        "Миколаївський": "Миколаївська обл.", "Баштанський": "Миколаївська обл.", "Вознесенський": "Миколаївська обл.", "Первомайський": "Миколаївська обл.",  # noqa: E501
        # Одеська
        "Одеський": "Одеська обл.", "Березівський": "Одеська обл.", "Подільський": "Одеська обл.", "Білгород-Дністровський": "Одеська обл.", "Ізмаїльський": "Одеська обл.", "Болградський": "Одеська обл.", "Роздільнянський": "Одеська обл.",  # noqa: E501
        # Хмельницька
        "Хмельницький": "Хмельницька обл.", "Кам'янець-Подільський": "Хмельницька обл.", "Шепетівський": "Хмельницька обл.",
        # Волинська
        "Луцький": "Волинська обл.", "Володимирський": "Волинська обл.", "Камінь-Каширський": "Волинська обл.", "Ковельський": "Волинська обл.",
        # Дніпропетровська
        "Дніпровський": "Дніпропетровська обл.", "Кам'янський": "Дніпропетровська обл.", "Криворізький": "Дніпропетровська обл.", "Нікопольський": "Дніпропетровська обл.", "Новомосковський": "Дніпропетровська обл.", "Самарівський": "Дніпропетровська обл.", "Павлоградський": "Дніпропетровська обл.", "Синельниківський": "Дніпропетровська обл.",  # noqa: E501
        # Житомирська
        "Житомирський": "Житомирська обл.", "Бердичівський": "Житомирська обл.", "Коростенський": "Житомирська обл.", "Звягельський": "Житомирська обл.",  # noqa: E501
        # Кіровоградська
        "Кропивницький": "Кіровоградська обл.", "Олександрійський": "Кіровоградська обл.", "Голованівський": "Кіровоградська обл.", "Новоукраїнський": "Кіровоградська обл.",  # noqa: E501
        # Чернівецька
        "Чернівецький": "Чернівецька обл.", "Вижницький": "Чернівецька обл.", "Дністровський": "Чернівецька обл.",
    }
    # fmt: on

    # Extract base dynamic token prefix name (e.g., 'Харківський')
    base_prefix = norm_name.split()[0] if norm_name and norm_name.split() else ""

    if base_prefix in district_to_oblast_map:
        normalized_oblast = district_to_oblast_map[base_prefix]
        return [normalized_oblast]

    if norm_name in config.EXTENDED_MAPPING_MATRIX:
        return [norm_name]

    return []


def process_rest_update(payload_dict: dict) -> None:  # noqa: C901, PLR0912, PLR0915
    """Process bulk REST data snapshot frames mapping onto systemic trees across 3 dynamic layouts."""
    kyiv_now = datetime.now(config.CURRENT_TZ).isoformat()

    packet_registry = {
        region_key: {
            "has_red_air": False,
            "has_yellow_air": False,
            "has_artillery": False,
            "has_urban": False,
            "latest_dt": None,
        }
        for region_key in config.EXTENDED_MAPPING_MATRIX
    }

    raw_block = payload_dict.get("alerts", [])

    # --- FORMAT SCHEME DETECTOR DAEMON ENGINE ---
    is_scheme_aiu = False
    is_scheme_klimenko = False

    # Safely detect the API schema format based on data types and key existence
    if isinstance(raw_block, list) and len(raw_block) > 0:
        first_item = raw_block[0]
        if isinstance(first_item, dict) and "location_title" in first_item:
            is_scheme_aiu = True
    elif isinstance(raw_block, dict):
        is_scheme_klimenko = True

    # --- GATE A: PROCESS SCHEME UAL (OFFICIAL STRUCTURE) ---
    if not is_scheme_aiu and not is_scheme_klimenko and isinstance(raw_block, list):
        for alert in raw_block:
            if not isinstance(alert, dict):
                continue

            r_name = alert.get("regionName")
            r_type = alert.get("regionType")
            target_keys = get_target_matrix_regions(r_name, r_type)

            for active_alert in alert.get("activeAlerts", []):
                if not isinstance(active_alert, dict):
                    continue

                alert_type = active_alert.get("type", "").upper()
                dt_object = parse_iso_time(active_alert.get("lastUpdate"))

                for key in target_keys:
                    if dt_object and (not packet_registry[key]["latest_dt"] or dt_object > packet_registry[key]["latest_dt"]):
                        packet_registry[key]["latest_dt"] = dt_object
                    if alert_type == "AIR":
                        for lvl in active_alert.get("activeAlertLevels", []):
                            if not isinstance(lvl, dict):
                                continue

                            lvl_str = str(lvl.get("alertLevel", "")).upper()
                            if lvl_str == "RED":
                                packet_registry[key]["has_red_air"] = True
                            elif lvl_str == "YELLOW":
                                packet_registry[key]["has_yellow_air"] = True
                    elif alert_type == "ARTILLERY":
                        packet_registry[key]["has_artillery"] = True
                    elif alert_type == "URBAN_FIGHTS":
                        packet_registry[key]["has_urban"] = True

    # --- GATE B: PROCESS SCHEME AIU (ALERTS.IN.UA FLAT ARRAY) ---
    elif is_scheme_aiu and isinstance(raw_block, list):
        for item in raw_block:
            if not isinstance(item, dict):
                continue

            loc_title = item.get("location_title")
            loc_type = item.get("location_type")
            target_keys = get_target_matrix_regions(loc_title, loc_type)

            alert_type = item.get("alert_type", "").upper()
            lvl_str = str(item.get("alert_level", "")).upper()
            dt_object = parse_iso_time(item.get("started_at"))

            for key in target_keys:
                if dt_object and (not packet_registry[key]["latest_dt"] or dt_object > packet_registry[key]["latest_dt"]):
                    packet_registry[key]["latest_dt"] = dt_object
                if alert_type == "AIR_RAID":
                    if lvl_str == "RED":
                        packet_registry[key]["has_red_air"] = True
                    elif lvl_str == "YELLOW":
                        packet_registry[key]["has_yellow_air"] = True
                elif alert_type == "ARTILLERY_SHELLING":
                    packet_registry[key]["has_artillery"] = True
                elif alert_type == "URBAN_FIGHTS":
                    packet_registry[key]["has_urban"] = True

    # --- GATE C: PROCESS SCHEME KLIMENKO (NESTED DICTIONARY KEY OBJECT) ---
    elif is_scheme_klimenko and isinstance(raw_block, dict):
        for oblast_raw_name, oblast_node in raw_block.items():
            if not isinstance(oblast_node, dict):
                continue

            if oblast_node.get("enabled"):
                target_keys = get_target_matrix_regions(oblast_raw_name, "State")
                dt_object = parse_iso_time(oblast_node.get("enabled_at"))
                lvl_str = str(oblast_node.get("alert_level", "")).upper()
                for key in target_keys:
                    if dt_object and (not packet_registry[key]["latest_dt"] or dt_object > packet_registry[key]["latest_dt"]):
                        packet_registry[key]["latest_dt"] = dt_object
                    if lvl_str == "YELLOW":
                        packet_registry[key]["has_yellow_air"] = True
                    else:
                        packet_registry[key]["has_red_air"] = True

            districts_block = oblast_node.get("districts", {})
            if isinstance(districts_block, dict):
                for district_raw_name, district_node in districts_block.items():
                    if not isinstance(district_node, dict):
                        continue

                    if district_node.get("enabled"):
                        target_keys = get_target_matrix_regions(district_raw_name, "District")
                        dt_object = parse_iso_time(district_node.get("enabled_at"))
                        lvl_str = str(district_node.get("alert_level", "")).upper()
                        for key in target_keys:
                            if dt_object and (not packet_registry[key]["latest_dt"] or dt_object > packet_registry[key]["latest_dt"]):
                                packet_registry[key]["latest_dt"] = dt_object
                            if lvl_str == "YELLOW":
                                packet_registry[key]["has_yellow_air"] = True
                            else:
                                packet_registry[key]["has_red_air"] = True

    # --- PHASE 3: COMMIT AGGREGATED METRICS TO GLOBAL STATE ---
    for region_key, metrics in packet_registry.items():
        states = config.state_cache["states"][region_key]

        # 1. Committing Alerts
        was_air_enabled = bool(states["alerts"]["enabled"])
        final_air_enabled = metrics["has_red_air"] or metrics["has_yellow_air"]
        final_air_yellow = metrics["has_yellow_air"] and not metrics["has_red_air"]

        states["alerts"]["enabled"] = final_air_enabled
        states["alerts"]["yellow"] = final_air_yellow
        if final_air_enabled:
            states["alerts"]["updated"] = metrics["latest_dt"].isoformat() if metrics["latest_dt"] else kyiv_now
        elif was_air_enabled:
            states["alerts"]["updated"] = kyiv_now

        # 2. Committing Threats
        threat_node = states["threats"]
        was_artillery = bool(threat_node["artillery"])
        was_urban = bool(threat_node["urban"])

        # Detect changes in specific indicators provided by this REST snapshot
        artillery_changed = was_artillery != metrics["has_artillery"]
        urban_changed = was_urban != metrics["has_urban"]

        # Commit current REST metrics directly
        threat_node["artillery"] = metrics["has_artillery"]
        threat_node["urban"] = metrics["has_urban"]

        for k in ["chemical", "nuclear", "drones", "missiles", "kabs", "ballistic", "explosions", "recon"]:
            threat_node[k] = False

        final_threatened = bool(metrics["has_artillery"] or metrics["has_urban"])
        was_threatened = was_artillery or was_urban

        if final_threatened:
            if not was_threatened:
                # First threat appeared in the region: update timestamp
                threat_node["updated"] = kyiv_now
            elif artillery_changed or urban_changed:
                # Operational situation changed within active threats: update timestamp
                threat_node["updated"] = kyiv_now
        elif was_threatened:
            # Absolute clarity achieved (transition from True -> False): lock clearing time strictly once
            threat_node["updated"] = kyiv_now

    config.state_cache["updated"] = kyiv_now
    LOGGER.info("⚡ [REST] Memory Sync: Cache updated successfully matching structured data frames.")
