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

**Alert Map Proxy Server** A lightweight connector that tracks air raid sirens and tactical threat data across Ukraine in real time. It automatically processes live information from the data feed and converts it into a clean, simple format perfect for integration with `Home Assistant` or custom smart home dashboards.

## Architecture

![Supports amd64 Architecture][amd64-shield] ![Supports aarch64 Architecture][aarch64-shield] ![Supports armv7 Architecture][armv7-shield] ![Supports armhf Architecture][armhf-shield] ![Supports i386 Architecture][i386-shield]

## Installation

Add the repository URL under **Supervisor → Add-on Store** in your Home Assistant front-end:

    https://github.com/andrewjswan/alert-map-proxy-addon/

<br />

## Data sources (providers):

> [!IMPORTANT]
>
> - **JAAM** [jaam.net.ua](https://jaam.net.ua/)
> - **Neptun** [neptun.in.ua](https://neptun.in.ua/)
> - **REST** [ubilling.net.ua](https://ubilling.net.ua/)

[amd64-shield]: https://img.shields.io/badge/amd64-yes-blue.svg
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-blue.svg
[armv7-shield]: https://img.shields.io/badge/armv7-no-red.svg
[armhf-shield]: https://img.shields.io/badge/armhf-no-red.svg
[i386-shield]: https://img.shields.io/badge/i386-no-red.svg
