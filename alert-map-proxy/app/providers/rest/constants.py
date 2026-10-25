import os

# Parse and build dynamic URI tracking array splitting the environment token stream directly
URI_LIST = [url.strip() for url in os.getenv("PROXY_ALERT_URL", "https://ubilling.net.ua/aerialalerts/?source=klimenko&raw|https://ubilling.net.ua/aerialalerts/?source=aiu&raw|https://ubilling.net.ua/aerialalerts/?source=ual&raw").split("|") if url.strip()]

# Polling interval rate in seconds to prevent server rate limiting
POLL_INTERVAL_SEC = 3

# Maximum allowed age of cached data in minutes before falling back to the next source
MAX_CACHE_AGE_MINUTES = 5

# Realistic Google Chrome User-Agent header string to bypass firewalls
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
