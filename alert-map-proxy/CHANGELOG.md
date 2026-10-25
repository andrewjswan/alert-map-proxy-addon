# Changelog

## 2026.10.9 - 2026-10-25

- Publish to Github

## 2026.10.9 - 2026-10-21

- Add `JAAM` as provider

## 2026.10.7 - 2026-10-20

### Ingestion & Architecture Enhancements

- **Thread-Safe Cache Synchronizer**: Integrated `threading.Event` across all ingestion channels to shield the `state_cache` database tree.
- **Zero-Stale HTTP Gateway Routing**: Enforced a strict non-blocking worker thread locking state logic (`cache_ready_event`). Incoming HTTP route requests on Bottle server now smoothly pause during runtime JSON tree assembly, safely avoiding race conditions and entirely eliminating empty or partially mutated data responses during startup and connection drops.

## 2026.10.5 - 2026-10-20

- Add `host_network` to App config

## 2026.10.3 - 2026-10-15

- Rename `UAM` provider to `REST`
- Add `Ukraine Alarm Map` as subprovider
- Add `Vadym Klymenko` as subprovider
- Add `Alerts in UA` as subprovider

## 2026.10.1 - 2026-10-15

- Add `Ukraine Alarm Map` as provider

## 2026.9.3 - 2026-09-23

- Add `Neptun` as provider

## 2026.9.1 - 2026-09-09

- Initial release.
