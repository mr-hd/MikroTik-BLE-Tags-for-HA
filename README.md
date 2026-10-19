# MikroTik BLE Tags

## Important note
**THIS IS NOT AN OFFICIAL MIKROTIK INTEGRATION.**

This is a community integration for Home Assistant that works with MikroTik Bluetooth tags.

Tested on:
- Home Assistant OS **2026.1.1**
- Home Assistant Container **2025.5.3**

Supported devices:
- [**TG-BT5-OUT**](https://mikrotik.com/product/tg_bt5_out)
- [**TG-BT5-IN**](https://mikrotik.com/product/tg_bt5_in)

---

## Features
- RSSI
- Temperature
- Battery level
- Accelerometer (X / Y / Z)
- Uptime
- Raw manufacturer data
- Fully configurable via UI (config flow)
- No cloud or internet required

---

## Before you start
Make sure your tag is **actively broadcasting** data.

You can verify this using:
- **MikroTik Beacon Manager**  
  https://help.mikrotik.com/docs/spaces/UM/pages/105742453/MikroTik+Beacon+Manager
- **Home Assistant**  
  `Settings → Bluetooth → Advertisement monitor`  
  Filter by your tag’s MAC address and confirm that advertisements are visible.

---

## Setting up the integration

### 1. Add the integration

At the moment, this integration must be installed as a **custom repository** via HACS.

1. Open **HACS**
2. Go to **Integrations**
3. Open the menu (⋮) → **Custom repositories**
4. Add this repository URL
5. Install the integration
6. Restart Home Assistant

After installation, add the integration via:
Go to:
`Settings → Devices & Services → Add Integration → MikroTik BLE Tags`  

If the integration is already added, click **Add entry**.

---

### 2. Configure the tag
Enter:
- Tag **MAC address**
- A **friendly name**  
  (This does not affect the tag itself; it is only stored in Home Assistant.)

![Tag MAC address setup](https://github.com/user-attachments/assets/5f384491-2ed9-49ff-9ac1-9e47306d56f1)

---

### 3. Verify device and entities
After submitting the form:
- One **device** will be created
- Multiple **entities** will appear with the reported parameters

![Created device and entities](https://github.com/user-attachments/assets/bcb7eabc-6fa4-41f6-a6a5-3be24e083f56)

---

## Non-obvious features

### Temperature unit conversion
Temperature is **natively converted** between °C and °F according to Home Assistant settings:
`Settings → System → General → Unit system`

---

### Human-readable uptime
Uptime is reported in seconds as the main sensor value, but a **human-readable format** is available in the entity attributes.

![Human readable uptime attribute](https://github.com/user-attachments/assets/73ae9e6d-1e1c-458b-93ad-24733563a60d)

---

## Notes
- Bluetooth support is required on the Home Assistant host
- This integration does **not** require internet access
- Device and entity names can be freely customized in Home Assistant
