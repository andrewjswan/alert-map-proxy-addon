"""Alert Map Proxy Server."""

import asyncio
import logging
from threading import Thread

import config
import web_server

# Initialize module-level logger
LOGGER = logging.getLogger("AMP")

if __name__ == "__main__":
    LOGGER.info("🌐 Spawning internal HTTP microserver thread engine...")
    http_thread = Thread(target=web_server.run_http_server, daemon=True)
    http_thread.start()
    LOGGER.info("✅ HTTP server running on port %d. JSON stack bound.", config.HTTP_SERVER_PORT)

    try:
        # Dynamically fetch the run_provider function for the selected engine
        from providers import get_active_provider_client

        run_active_provider = get_active_provider_client()

        # Execute the targeted asynchronous background loop
        asyncio.run(run_active_provider())
    except KeyboardInterrupt:
        LOGGER.info("\n🛑 Stopped by user command.")
