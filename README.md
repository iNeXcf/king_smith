# King Smith Walking Pad for Home Assistant

[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

A custom Home Assistant integration for local Bluetooth control of King Smith
WalkingPads. It provides start/stop control, a speed control in km/h, live session
data, and persistent totals for distance, duration, and steps.

This fork adds FTMS support and the King Smith unlock sequence required by the
Z1 advertised as `KS-HD-Z1D`. It targets Home Assistant 2026.11.2 or newer.
The original integration also supports the C2 and A1 Pro through the legacy
WiLink protocol.

## Requirements

- Home Assistant 2026.11.2 or newer.
- A local Bluetooth adapter or an ESPHome Bluetooth proxy that supports active
  connections.
- The WalkingPad must be powered on and in Bluetooth range.
- KS Fit and other apps must be fully closed. A BLE device can normally maintain
  only one control connection at a time.

## Install with HACS

1. Open HACS, select the three-dot menu, and choose **Custom repositories**.
2. Add `https://github.com/koalexbear/king_smith` as an **Integration**.
3. Open **King Smith Walking Pad** and select **Download**. If HACS asks for a
   version, choose `main`.
4. Restart Home Assistant.

When updating an existing installation, refresh the repository information in
HACS and choose **Redownload** if the new version is not shown immediately.

## Add the WalkingPad

You normally do **not** need to know or type a MAC address.

1. Power on the Z1 and fully close KS Fit.
2. Wait up to 30 seconds so the local adapter or a Bluetooth proxy can report an
   advertisement.
3. Open **Settings → Devices & services**. If Home Assistant shows a discovered
   **King Smith Walking Pad**, select **Configure**.
4. Otherwise select **Add integration → King Smith Walking Pad**.
5. Choose `KS-HD-Z1D (…)` from the **WalkingPad** drop-down, assign a friendly
   name, and submit the form.

The value in parentheses is the Bluetooth address detected by Home Assistant.
It identifies the physical device across the local adapter and all proxies. The
integration stores it so it can reconnect to the same WalkingPad later; you do
not need to obtain it yourself when the device appears in the list.

Manual address entry is only a fallback for installations where Home Assistant
can reach the device but has not yet displayed it in the drop-down. Find the
address under **Settings → Devices & services → Bluetooth → Advertisement
monitor**, locate the entry whose local name is `KS-HD-Z1D`, and copy its
Bluetooth address. Do not enter the Raspberry Pi's address, the proxy's address,
or the address of a phone.

If the list is empty, check that:

- the WalkingPad is on and KS Fit is disconnected;
- at least one adapter or proxy reports it as connectable;
- the proxy is close enough to the WalkingPad;
- you waited for a fresh advertisement after opening the setup dialog.

## Controls and sensors

The switch starts or stops the belt. The speed slider covers 1.0–6.0 km/h in
the same 0.1 km/h increments as KS Fit. The separate Sleep button stops the
belt if necessary and then puts the Z1 into its low-power mode. Wake the Z1
with its physical remote.

Live sensors include speed, session distance, session duration, steps, and step
cadence. Values can remain **Unknown** until the first corresponding Bluetooth
report arrives. Total distance, duration, and steps are restored after a Home
Assistant restart. Sessions completed entirely while Home Assistant is offline
cannot be recovered unless the WalkingPad reports that history later.

## Troubleshooting

Enable debug logging for this integration from its Home Assistant integration
page. For protocol details, also set `walkingpad_controller` to debug. When
reporting a problem, include the exact setup or connection error, relevant log
lines, the advertised Bluetooth name, and whether the connection uses the local
adapter or an ESPHome proxy.

The protocol implementation uses
[walkingpad-controller](https://github.com/mcdax/walkingpad-controller). The Z1
unlock sequence is documented by
[z1-walkingpad-mcp](https://github.com/slandau3/z1-walkingpad-mcp#how-it-works-the-protocol).

## Manual installation

1. Copy `custom_components/king_smith` from this repository into the
   `custom_components` directory inside your Home Assistant configuration
   directory.
2. Restart Home Assistant.
3. Follow **Add the WalkingPad** above.

Contributions and hardware test reports are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md).

[commits-shield]: https://img.shields.io/github/commit-activity/y/koalexbear/king_smith.svg?style=for-the-badge
[commits]: https://github.com/koalexbear/king_smith/commits/main
[license-shield]: https://img.shields.io/github/license/koalexbear/king_smith.svg?style=for-the-badge
