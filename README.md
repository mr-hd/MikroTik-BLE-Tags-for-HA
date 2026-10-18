<picture>
  <source media="(prefers-color-scheme: dark)" srcset="custom_components/mikrotik_ble_tags/brand/dark_logo.png">
  <img alt="MikroTik" src="custom_components/mikrotik_ble_tags/brand/logo.png" width="340">
</picture>

# MikroTik BLE Tags

Community integration for MikroTik TG-BT5-IN and TG-BT5-OUT Bluetooth tags.
This project is not an official MikroTik integration.

[Install with HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=mr-hd&repository=MikroTik-BLE-Tags-for-HA&category=integration)
· [Set up an installed integration](https://my.home-assistant.io/redirect/config_flow_start/?domain=mikrotik_ble_tags)

## Requirements

- Home Assistant 2025.5.3 or newer.
- A configured Bluetooth adapter or supported Bluetooth proxy in range.
  Receive-only adapters/proxies are supported; no connection to the tag is needed.
- Configure the tag in MikroTik Beacon Manager to broadcast **MikroTik v1 telemetry**,
  with **encryption disabled** and periodic advertisements enabled.
- Local bundled icons and logos are displayed by Home Assistant 2026.3 and newer.
  Earlier supported versions can use the integration but may show a generic icon.

iBeacon, Eddystone and encrypted MikroTik telemetry are not decoded by this integration.
A tag's available measurements depend on its hardware and firmware.

## Install

### HACS

Until the repository is accepted into the default catalog:

1. Open HACS and its menu > Custom repositories.
2. Add https://github.com/mr-hd/MikroTik-BLE-Tags-for-HA with category Integration.
3. Download MikroTik BLE Tags.
4. Restart Home Assistant if requested.
5. Open Settings > Devices & services. Confirm a discovered tag, or select
   Add integration > MikroTik BLE Tags and enter its MAC address.

After catalog acceptance, search for MikroTik BLE Tags directly in HACS.
The repository badge above also provides a direct installation route.

### Manual installation

1. Download a source release and extract it.
2. Copy only `custom_components/mikrotik_ble_tags/` into your Home Assistant
   configuration's `custom_components/` directory.
3. Restart Home Assistant and add the integration as described above.

### Update from 1.0.0

Back up Home Assistant first. Replace the complete integration directory with the
new one, then restart. Do not delete the integration, recreate its entities, or
delete the recorder database. The domain, config-entry identity and entity unique
IDs are retained, so registered entity IDs and their history can be reused.

The new Raw diagnostic entity is disabled by default. Home Assistant preserves
existing entity-registry choices, so an already enabled Raw entity remains
enabled after updating. You may disable it manually to reduce recorded packet data.

## Add a tag

Bluetooth discovery offers supported nearby tags automatically. Confirm the tag
and choose its name. Already configured MAC addresses are not offered again.

For manual setup, enter a colon-separated MAC address and a friendly name.
Home Assistant must have seen a supported unencrypted packet, or receive one
during the 15-second setup wait. Empty names fall back to MikroTik Tag.

Use Bluetooth > Advertisement monitor to check that the correct tag and
manufacturer data are visible.

## Entities

| Entity | Unit | Long-term statistics |
| --- | --- | --- |
| Temperature | °C, converted by HA when requested | Yes |
| Battery | % | Yes |
| RSSI | dBm | Yes |
| Acc X / Y / Z | G, retained from earlier releases | Yes |
| Uptime | seconds | Yes |
| Raw | text and packet attributes; disabled by default | No |

RSSI, uptime and Raw are diagnostic entities. Uptime also retains its
`uptime_human` attribute. The model is shown generically as TG-BT5 because the
telemetry format does not reliably identify the exact product variant.

### Long-term history

Numerical sensors expose `state_class: measurement`. If included in recorder,
Home Assistant keeps hourly minimum/mean/maximum statistics indefinitely.
Detailed state history and five-minute statistics still follow the recorder
retention setting, which defaults to ten days. This does not archive every
Bluetooth packet forever, and cannot restore already purged history.

### Availability

When Bluetooth determines a tag is no longer being seen, its entities become
unavailable. Availability follows Home Assistant's learned advertising interval.
The entities recover when valid advertisements return.

Unsupported, missing or encrypted telemetry is never reused as fresh sensor
data. RSSI can remain available while the tag is heard but its telemetry cannot
be decoded. Disabled accelerometer axes and out-of-range battery values are
unavailable individually.

## Troubleshooting

- **No scanner:** configure the Bluetooth integration or a supported proxy.
- **Tag not found:** check its MAC, range and periodic advertising configuration.
- **Unsupported packet:** choose MikroTik telemetry rather than iBeacon/Eddystone.
- **Encrypted packet:** turn off packet encryption in MikroTik Beacon Manager.
- **Intermittent unavailable:** check radio range and periodic advertising.
  Trigger-only tags can legitimately be unavailable between transmissions.
- **Only ten days of old history:** hourly statistics start accumulating after
  installing this update. Check the sensor's state_class and the Statistics tab.
- **Raw diagnostics:** enable the Raw entity on the device's entity list when
  needed. It includes packet bytes, telemetry status, flags and encryption status.

## Remove

Open Settings > Devices & services > MikroTik BLE Tags, open the tag entry's
menu and delete it. Remove the custom integration from HACS if no longer needed,
and restart if requested. Bluetooth and entity subscriptions are cleaned up.

## Development

Tests use Home Assistant 2026.10.2 and Python 3.14:

```bash
python -m pip install -r requirements_test.txt
ruff check .
ruff format --check .
pytest --cov=custom_components.mikrotik_ble_tags --cov-report=term-missing
```

CI also runs the same suite against the minimum supported Home Assistant
2025.5.3 on Python 3.13, using requirements_test_minimum.txt.

See [SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md) for publishing and catalog steps,
[CHANGELOG.md](CHANGELOG.md) for changes, and [TEST_REPORT.md](TEST_REPORT.md) for
what was actually verified. HACS validation and Hassfest run through GitHub Actions.

## References and artwork

- [MikroTik advertisement format](https://help.mikrotik.com/docs/spaces/UM/pages/105742533/MikroTik+Tag+advertisement+formats)
- [Home Assistant long-term statistics](https://www.home-assistant.io/docs/configuration/long-term-statistics/)
- [Brand asset provenance](BRAND_ASSETS.md)

Code is distributed under the included MIT license. MikroTik artwork remains
third-party brand material; see the provenance file.
