<div align="center">
<h1>Home Assistant App: Alert Map Proxy</h1>
</div>

## General

[![ha app_badge](https://img.shields.io/badge/HA-App-blue.svg)](https://developers.home-assistant.io/docs/add-ons)
[![Alert Map Proxy](https://img.shields.io/badge/Alert_Map-Proxy-blue.svg)](https://github.com/andrewjswan/alert-map-proxy-addon/)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/andrewjswan/alert-map-proxy-addon/build.yml?logo=github)](https://github.com/andrewjswan/alert-map-proxy-addon/actions)
[![GitHub release (latest SemVer including pre-releases)](https://img.shields.io/github/v/release/andrewjswan/alert-map-proxy-addon?include_prereleases)](https://github.com/andrewjswan/alert-map-proxy-addon/blob/master/alert-map-proxy/CHANGELOG.md)
[![GitHub License](https://img.shields.io/github/license/andrewjswan/alert-map-proxy-addon?color=blue)](https://github.com/andrewjswan/alert-map-proxy-addon/blob/master/LICENSE)
[![StandWithUkraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraine.svg)](https://github.com/vshymanskyy/StandWithUkraine/blob/main/docs/README.md)

**Alert Map WebSocket Proxy Server** A lightweight connector that tracks air raid sirens and tactical threat data across Ukraine in real time. It automatically processes live information from the data feed and converts it into a clean, simple format perfect for integration with `Home Assistant` or custom smart home dashboards. 

## Architecture

![Supports amd64 Architecture][amd64-shield] ![Supports aarch64 Architecture][aarch64-shield] ![Supports armv7 Architecture][armv7-shield] ![Supports armhf Architecture][armhf-shield] ![Supports i386 Architecture][i386-shield]

## Key Features

* **Real-Time Data Processing:** Receives instant live updates on air alerts and security events without any delays.
* **Smart Dashboard Protection:** Cleverly filters out duplicate data or temporary transmission errors, ensuring your smart home indicators never freeze or flicker.
* **Intelligent Regional Links:** Automatically understands when a minor local threat affects an entire region or province, keeping your family accurately informed.
* **Self-Healing Connection:** Automatically wipes old data during network disconnections so your system never shows ghost or outdated warnings.

## Configuration Parameters

The proxy server behavior can be adjusted using standard environment variables or a configuration sheet. Below is the strict schema definition for setting up your environment:

| Variable / Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `provider` | `list` | **Yes** | Data provider (`JAAM`, `NEPTUN`, `REST`). |
| `alert_url` | `str` | No | Alternative endpoint for streaming data. |
| `use_aggregation` | `bool` | No | Enables regional bottom-up data cascading. Defaults to `True`. |
| `log_level` | `list` | No | Active logging filtering layer (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |

> [!IMPORTANT]
> Data sources (providers):
>
> - **JAAM** [jaam.net.ua](https://jaam.net.ua/)
> - **Neptun** [neptun.in.ua](https://neptun.in.ua/)
> - **REST** [ubilling.net.ua](https://ubilling.net.ua/)

## Available API Endpoints

Once running, the server provides web links (endpoints) that you can easily plug into `Home Assistant` rest sensors.

### 1. Complete System View
* **Link:** `GET /`
* **What it does:** Provides a full overview of the current status for all cities and regions.

### 2. Simple Numeric Status Tracker
* **Link:** `GET /status/<region_id>`
* **What it does:** Returns a simple code indicating the alert level for a specific region ID:
  * `1`: **High Alert** Full primary air raid sirens are active.
  * `2`: **Low Alert** A quiet/yellow advisory status is active.
  * `0`: **Safe** No active air alerts.
  * `-1`: **Error** The requested region ID was not recognized.

### 3. Detailed Region Status
* **Link:** `GET /states/<region_id>`
* **What it does:** Shows everything happening in that specific region, including all tracked threats (such as drones or missiles) and exact timestamps, along with the readable name.

### 4. Combined Multi-Region Status Summary
* **Link:** `GET /states/summary?ids=<region_id>,<region_id>,<region_id>`
* **What it does:** Allows you to check the status of multiple cities or regions at the same time using a single web link. It is perfect for grouping neighboring areas together on your dashboard.
* **How the result works:**
  * `1`: **High Alert** At least one of the checked regions has a full primary air raid siren active. Red alerts always take top priority.
  * `2`: **Low Alert** There are no primary red sirens, but at least one checked region has a quiet/yellow advisory status active.
  * `0`: **Safe** Absolutely none of the specified regions have any active air alerts (everything is completely clear).
  * `-1`: **Error** The `ids` parameter is missing or none of the provided numbers matched any recognized regions.

**Sample Request:** `GET /states/summary?ids=31,332`

### 5. Flat Region Status Summary
* **Link:** `GET /states/flat`
* **What it does:** Returns a highly optimized, flat key-value list of all regions with their simplified numeric status codes. It allows your dashboard to read the state of the entire country using a single, lightweight request.
* **Response Values:**
  * `0`: Safe. No active air alerts.
  * `1`: High Alert. Full primary air raid sirens are active.
  * `2`: Low Alert. A quiet/yellow advisory status is active.

### 6. Packed Mathematical Bitmap Vector
* **Link:** `GET /states/packed?timeout=5`
* **What it does:** The most powerful, data-saving endpoint. It compresses the entire live situation of a region (the siren status combined with any of the 10 types of active threats like drones or missiles) into a single, clean integer value.
* **Sliding Expiration Filter (`timeout` parameter):** You can pass an optional `timeout` window in minutes (e.g., `?timeout=5`). The proxy server checks the exact age of the specific threat. If the threat data hasn't been updated within that window, it is considered expired and safely wiped from the calculation in real-time, preventing stale indicators.
* **How to read the packed numbers:**
  * `0`: Completely Clear. No active sirens and no tactical threats.
  * `Below 10000`: Sirens are off, but a localized threat is active. The number equals the raw threat bitmask (e.g., `32` means strike drones are detected, `1024` means a reconnaissance drone is active).
  * `10000 + threat_bitmask`: High/Red Alert siren is active. (e.g., `10032` means Red Alert due to strike drones).
  * `20000 + threat_bitmask`: Low/Yellow Alert status is active. (e.g., `20032` means Yellow Alert due to strike drones).

**Sample Request:** `GET /states/packed?timeout=5`

#### Threat Bitmask Specification Reference

To decode any tactical threat value below `10000` (or after subtracting `10000` / `20000` from the packed alert status), use a standard bitwise AND operation against these exact hardware- firmware bit values. 

If multiple threats are active simultaneously, their values are added together (e.g., Drones + Missiles = 32 + 64 = 96).

| Bit Position | Integer Value | Code Marker | Tactical Threat Description |
| :--- | :--- | :--- | :--- |
| `1 << 1` | `2` | `ARTILLERY` | Artillery hazard strike warning active |
| `1 << 2` | `4` | `URBAN` | Localized proximity urban combat danger |
| `1 << 3` | `8` | `CHEMICAL` | Localized chemical event threshold warning |
| `1 << 4` | `16` | `NUCLEAR` | Nuclear or critical infrastructure escalation threat |
| `1 << 5` | `32` | `DRONES` | Strike UAV / Shahed tactical deployment warning |
| `1 << 6` | `64` | `MISSILES` | Cruise or guided missile tracking indicator active |
| `1 << 7` | `128` | `KABS` | Tactical guided aerial bomb (KAB) warning layer |
| `1 << 8` | `256` | `BALLISTIC` | High-altitude strategic ballistic launch confirmed |
| `1 << 9` | `512` | `EXPLOSION` | Verified dynamic kinetic impact event or explosion |
| `1 << 10` | `1024` | `RECON_DRONES`| Strategic surveillance reconnaissance drone active |

**Decoding Example (Home Assistant Template or Script):**
If the proxy returns `10096` for a region:
1. `10096` is in the 10000 range -> **Primary Red Alert Siren is ON**.
2. Subtract `10000` -> Remaining threat bitmask is `96`.
3. `96 & 64` is true -> **Missiles are active**.
4. `96 & 32` is true -> **Drones are active**.

### 7. Custom YAML-Mapped Regional Entities
* **Link:** `GET /states/map` or `GET /states/map?timeout=5`
* **Configuration File:** Requires a valid mapping layout stored at `/config/addons_config/alert_map_proxy/map.yaml`.
* **What it does:** Reads your custom hardware/zone ID groups from the YAML file on every request and maps them directly to the active air alert statuses. It allows you to distribute uniform statuses to completely custom tracking numbers or smart relays without changing a single line of backend code.
* **Sliding Threat Filter (`timeout` parameter):** When the optional `timeout` parameter is provided (e.g., `?timeout=5`), the endpoint tracks live tactical events (like drones or missiles) within that specific minute window. If a threat is active and fresh, the status code escalates to indicate immediate danger.

#### Advanced Output Status Matrix
Depending on whether the `timeout` parameter is active or omitted, the endpoint evaluates the environment using these codes:

| Output Code | Active Siren Layer | Tactical Threat Layer Status | Condition Context |
| :---: | :--- | :--- | :--- |
| **`0`** | Completely Clear | No active threats | Region is safe. |
| **`1`** | **Red Air Alert ON** | Expired or no tactical threats | Standard siren active. Default if `timeout` is missing. |
| **`2`** | **Yellow Air Alert ON**| Expired or no tactical threats | Silent warning active. Default if `timeout` is missing. |
| **`3`** | **Red Air Alert ON** | **Fresh Threat Detected** | Active siren + live tactical event within `timeout` window. |
| **`4`** | **Yellow Air Alert ON**| **Fresh Threat Detected** | Silent warning + live tactical event within `timeout` window. |

**Sample Request:** `GET /states/map?timeout=5`

### 8. Proxy Connection Pulse & Watchdog Health
* **Link:** `GET /health`
* **What it does:** Returns the operational health status of the connection pipeline between your proxy server and the remote telemetry provider. It exposes a reactive connection pulse, allowing Home Assistant to monitor connection quality and alert you instantly if the data stream drops.
* **How it works:** The proxy server explicitly sends manual heartbeat pings to the remote server. Upon receiving a response, it updates a global timestamp. The health status is evaluated dynamically based on how much time has passed since the last successful handshake or telemetry data block.

#### Advanced Connection Health Status Matrix

| Status Output | Stalled Window | System Condition | Automated Watchdog Action |
| :---: | :--- | :--- | :--- |
| **`online`** | 0 to 5 minutes | Perfect telemetry data stream or active ping/pong handshake. | Normal operation. |
| **`idle`** | 5 to 10 minutes | Telemetry stream is quiet, but connection layer is still responsive. | Monitoring pipeline status. |
| **`critical`** | 10 to 15 minutes | Prolonged server silence. Potential upstream data drop. | Awaiting recovery cutoff. |
| **`offline`** | Over 15 minutes | Connection completely frozen, crashed, or unresponsive. | **Force-dropping connection** and triggering full memory/cache cleanup to initiate a clean reconnect cycle. |

**Sample Request:** `GET /health`

<br />

> [!TIP]
> Data sources (providers):
>
> - **JAAM** [API Documentation](https://info.jaam.net.ua/fusion/api/server-api/)
> - **Neptun** [API Documentation](https://neptun.in.ua/developers)
> - **REST** [API Documentation](https://wiki.ubilling.net.ua/doku.php?id=aerialalertsapi)

> [!TIP]
> Buy a [JAAM Alarm Map](https://store.jaam.net.ua/)

[amd64-shield]: https://img.shields.io/badge/amd64-yes-blue.svg
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-blue.svg
[armv7-shield]: https://img.shields.io/badge/armv7-no-red.svg
[armhf-shield]: https://img.shields.io/badge/armhf-no-red.svg
[i386-shield]: https://img.shields.io/badge/i386-no-red.svg
