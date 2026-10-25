#!/usr/bin/with-contenv bashio

# ==============================================================================
# Home Assistant App: Alert Map Proxy
# ==============================================================================

bashio::log.blue "-----------------------------------------------------------"

bashio::log.info "$(bashio::app.name) Starting..."
export PROXY_VERSION=$(bashio::app.version)
bashio::log.info 'Configuration:'
bashio::log.blue "  Version: ${PROXY_VERSION}"
bashio::log.blue "  Architecture: $(bashio::info.arch)"
if bashio::config.has_value 'provider'; then
  export PROXY_PROVIDER=$(bashio::config 'provider')
  bashio::log.blue "  Provider: ${PROXY_PROVIDER}"
fi
if bashio::config.has_value 'alert_url'; then
  export PROXY_ALERT_URL=$(bashio::config 'alert_url')
  bashio::log.blue "  URL: ${PROXY_ALERT_URL}"
fi
if bashio::config.has_value 'use_aggregation'; then
  export USE_AGGREGATION=$(bashio::config 'use_aggregation')
  bashio::log.blue "  Aggregation: ${USE_AGGREGATION}"
fi
if bashio::config.has_value 'log_level'; then
  export LOG_LEVEL=$(bashio::config 'log_level')
fi

bashio::log.blue "-----------------------------------------------------------"

bashio::log.info "$(bashio::app.name) Started."

# ==============================================================================

bashio::color.reset
cd /app
python ./proxy.py
bashio::color.reset

# ==============================================================================

bashio::log.info
bashio::log.info "$(bashio::app.name) Stoped."
bashio::exit.ok
