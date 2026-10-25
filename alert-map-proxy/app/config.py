"""Alert Map Proxy Server - Configuration."""

import logging
import os
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

# --- SYSTEM WATCHDOG & HTTP CONFIGURATION CONSTANTS ---
# Timezone identifier used across the entire telemetry engine
SYSTEM_TIMEZONE_NAME = "Europe/Kyiv"

# HTTP server deployment network settings
HTTP_SERVER_HOST = "0.0.0.0"  # noqa: S104
HTTP_SERVER_PORT = 5550
HTTP_SERVER_ENGINE = "paste"
HTTP_SERVER_QUIET_MODE = True

# Watchdog connection freshness thresholds (in minutes)
HEALTH_ONLINE_THRESHOLD_MIN = 5.0
HEALTH_IDLE_THRESHOLD_MIN = 10.0
HEALTH_CRITICAL_THRESHOLD_MIN = 15.0
HEALTH_FATAL_RECONNECT_MIN = 30.0

# Asynchronous network socket read timeout interval (in seconds)
SOCKET_READ_TIMEOUT_SEC = 30.0
PIPELINE_RECONNECT_DELAY_SEC = 15

# WEB Server timeout
WEB_SERVER_TIMEOUT_SEC = 10.0

# Global timezone configuration
CURRENT_TZ = ZoneInfo(SYSTEM_TIMEZONE_NAME)

# Global timezone-aware timestamp to track connection pulse
last_heartbeat = datetime.now(CURRENT_TZ)

# Target provider state token assigned dynamically during initialization
ACTIVE_PROVIDER = os.getenv("PROXY_PROVIDER", "neptun").strip().lower()

# --- REGION CODES ---
EXTENDED_MAPPING_MATRIX = {
    "м. Київ": [31],
    "Київська обл.": [14, 77, 73, 75, 76, 74, 750, 8888, 79, 78, 31],
    "м. Вінниця": [155],
    "Вінницька обл.": [4, 32, 35, 36, 34, 33, 37, 155],
    "м. Луцьк": [225],
    "Волинська обл.": [8, 39, 38, 40, 41, 225],
    "м. Дніпро": [332],
    "Дніпропетровська обл.": [9, 43, 44, 47, 48, 42, 45, 46, 332],
    "Донецька обл.": [28, 56, 51, 55, 53, 49, 52, 50, 54],
    "м. Житомир": [442],
    "Житомирська обл.": [10, 59, 58, 57, 60, 442],
    "м. Ужгород": [500],
    "Закарпатська обл.": [11, 66, 61, 62, 63, 64, 65, 500],
    "м. Запоріжжя": [564],
    "Запорізька обл.": [12, 146, 145, 149, 147, 148, 564],
    "м. Івано-Франківськ": [632],
    "Івано-Франківська обл.": [13, 68, 67, 71, 72, 70, 69, 632],
    "м. Кропивницький": [761],
    "Кіровоградська обл.": [15, 81, 80, 82, 83, 761],
    "Луганська обл.": [16, 86, 85, 84, 87],
    "м. Львів": [845],
    "Львівська обл.": [27, 90, 89, 88, 91, 92, 94, 93, 845],
    "м. Миколаїв": [926],
    "Миколаївська обл.": [17, 96, 95, 97, 98, 926],
    "м. Одеса": [964],
    "Одеська обл.": [18, 105, 100, 104, 102, 103, 101, 99, 964],
    "м. Полтава": [1060],
    "Полтавська обл.": [19, 107, 106, 109, 108, 1060],
    "м. Рівне": [1133],
    "Рівненська обл.": [5, 110, 111, 112, 113, 1133],
    "м. Суми": [1187],
    "Сумська обл.": [20, 115, 116, 117, 114, 118, 1187],
    "м. Тернопіль": [1241],
    "Тернопільська обл.": [21, 119, 121, 120, 1241],
    "м. Харків": [1293],
    "Харківська обл.": [22, 124, 123, 122, 126, 127, 125, 128, 1293],
    "м. Херсон": [1370],
    "Херсонська обл.": [23, 131, 129, 130, 132, 133, 1370],
    "м. Хмельницький": [1400],
    "Хмельницька обл.": [3, 136, 134, 135, 1400],
    "м. Черкаси": [1473],
    "Черкаська обл.": [24, 153, 152, 150, 151, 1473],
    "м. Чернівці": [1542],
    "Чернівецька обл.": [26, 139, 138, 137, 1542],
    "м. Чернігів": [1591],
    "Чернігівська обл.": [25, 141, 142, 143, 140, 144, 1591],
    "АР Крим": [9999],
}

# --- IN-MEMORY GLOBAL CACHE TREE ---
state_cache = {
    "version": 1,
    "updated": None,
    "states": {
        region: {
            "alerts": {
                "enabled": False,
                "yellow": False,
                "updated": None,
            },
            "threats": {
                "artillery": False,
                "urban": False,
                "chemical": False,
                "nuclear": False,
                "drones": False,
                "missiles": False,
                "kabs": False,
                "ballistic": False,
                "explosions": False,
                "recon": False,
                "updated": None,
            },
        }
        for region in EXTENDED_MAPPING_MATRIX
    },
}

# Thread synchronization event to prevent serving stale or empty cache during ingestion
cache_ready_event = threading.Event()

# --- CONFIGURATION FILE PATH CONSTANT ---
YAML_CONFIG_PATH = "/config/addons_config/alert_map_proxy/map.yaml"

# --- LOGGING CONFIGURATION ---
ENV_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- CACHE PARSING ENGINE ---
USE_AGGREGATION = os.environ.get("USE_AGGREGATION", "True").strip().lower() in ("true", "1", "yes")


# --- LOGGING ---
# Custom log filter to drop aggressive background HTTP traffic logs completely
class SuppressWsgiFilter(logging.Filter):
    """Filter to suppress aggressive background HTTP traffic logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Supress WSGI messages in Debug Log."""
        # Drop logs if they contain standard web request markers or the consumer user-agent
        return not (record.name == "wsgi" and record.levelno <= logging.INFO)


# Initialize global logging subsystem configurations
root_logger = logging.getLogger()
handler = logging.StreamHandler()
handler.addFilter(SuppressWsgiFilter())

logging.basicConfig(
    level=ENV_LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[handler],
)

# Shut down aggressive third-party debug noise modules by force
logging.getLogger("paste.httpserver.ThreadPool").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("paste").setLevel(logging.WARNING)

# Dedicated logger instance for config module scope
LOGGER = logging.getLogger(__name__)
