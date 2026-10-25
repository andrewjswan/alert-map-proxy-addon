"""Alert Map Proxy Server - Provider Manager."""

import importlib
import config
import logging

# Initialize module-level logger
LOGGER = logging.getLogger(__name__)

def get_active_provider_client():
    """Dynamically imports and returns the active provider's client runner."""
    try:
        # Dynamically import e.g., providers.XXXXX.client
        provider_module = importlib.import_module(f"providers.{config.ACTIVE_PROVIDER}.client")
        return provider_module.run_provider
    except ImportError:
        import sys
        LOGGER.error(f"❌ Critical initialization failure: Provider '{config.ACTIVE_PROVIDER}' is invalid or not found.")
        LOGGER.info(f"💡 Supported values are matching directory names inside 'providers/' package.")
        sys.exit(1)
