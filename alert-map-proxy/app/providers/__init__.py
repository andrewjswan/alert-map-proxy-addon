"""Alert Map Proxy Server - Provider Manager."""

import importlib
import logging
import sys
from collections.abc import Callable

import config

# Initialize module-level logger
LOGGER = logging.getLogger(__name__)


def get_active_provider_client() -> Callable:
    """Dynamically imports and returns the active provider's client runner."""
    try:
        # Dynamically import e.g., providers.XXXXX.client
        provider_module = importlib.import_module(f"providers.{config.ACTIVE_PROVIDER}.client")
    except ImportError:
        LOGGER.exception("❌ Critical initialization failure: Provider '%s' is invalid or not found.", config.ACTIVE_PROVIDER)
        LOGGER.info("💡 Supported values are matching directory names inside 'providers/' package.")
        sys.exit(1)
    else:
        return provider_module.run_provider
