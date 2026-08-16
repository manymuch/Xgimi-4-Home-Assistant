# XGIMI Projector Remote for Home Assistant

<img src="https://brands.home-assistant.io/xgimi/logo.png" width="360" height="120" alt="XGIMI">

This HACS custom integration controls supported XGIMI projectors over the local
network. Normal remote commands use UDP. Power-on supports the `Automatic`,
`Local`, and `ESP32` wake backends; setup details are below.

## Installation
### HACS

[![Open your Home Assistant instance and add this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=manymuch&repository=Xgimi-4-Home-Assistant&category=integration)

1. Install [HACS](https://hacs.xyz/).
2. In HACS, open the menu and choose Custom repositories.
3. Add `https://github.com/manymuch/Xgimi-4-Home-Assistant` as an
   Integration repository.
4. Download XGIMI Projector Remote.
5. Restart Home Assistant.
6. Go to Settings → Devices & services → Add integration, search for
   XGIMI, and complete setup.

### Manual

Download a release and copy `custom_components/xgimi` into the Home Assistant
configuration directory, then restart Home Assistant.

Existing config entries upgrade in place. Their name, host, token, unique ID,
entity ID, and remote entity are preserved.


## Bluetooth Power-On Backend

### Backend 1: Automatic

Automatic mode prefers a configured ESPHome wake button. If no ESP32 wake
button is configured, it uses a local Bluetooth adapter that exposes BlueZ's
BLE advertising interface. If neither is available, the integration reports a
configuration/service error and creates a Repair.

When an ESP32 button is configured but unavailable, Automatic mode reports that
button as unavailable and does not silently fall back to local Bluetooth for
that wake operation.

### Backend 2: Local Bluetooth

The local backend uses the Home Assistant host's system D-Bus and BlueZ service.
It discovers adapters dynamically through
`org.freedesktop.DBus.ObjectManager` and selects only adapters exposing
`org.bluez.LEAdvertisingManager1`. It does not assume the adapter is `hci0`.

The transmitted advertisement is:

```text
Type: peripheral
Local name: Bluetooth 4.0 RC
Service UUID: 00001812-0000-1000-8000-00805f9b34fb
Manufacturer ID: 0x0046
Manufacturer payload: the configured XGIMI token
Appearance: 961
```

One advertisement is registered for four seconds by default, then unregistered.
The duration can be set from 1–10 seconds using the projector device's
Advertisement duration configuration entity. This advanced entity is
disabled by default.

### Diagnostics and debug logging

The integration options include **Enable debug logging**, disabled by default.
When enabled, the integration logs the selected wake backend, ESPHome button
validation and service-call result, BlueZ advertisement registration and
cleanup, and D-Bus errors. It also includes extended adapter diagnostics for
the BlueZ version, supported advertising features and includes, and controller
advertising capabilities.

#### Home Assistant OS

1. Attach a Bluetooth adapter to the Home Assistant host.
2. Install this integration through HACS and restart Home Assistant.
3. Add XGIMI from Settings → Devices & services → Add integration.
4. Select Local or Automatic, then enter the projector IP and BLE
   token.
5. Test wake-up.

The implementation uses the host's system BlueZ service directly; no add-on or
helper service is required. If no adapter is found, check Settings → Devices
& services → Bluetooth.

#### Home Assistant Container

The Docker host must run BlueZ. Home Assistant must use host networking, access
the host system D-Bus, and have the Bluetooth networking capabilities required
by the host setup.

Host networking is required in addition to the D-Bus mount. The host Bluetooth
adapter's HCI socket is exposed in the host network namespace; a bridge-network
container may be able to see `org.bluez` over D-Bus but still cannot open the
Bluetooth socket. That produces errors such as `Bluetooth adapter ... not
found` or `Unable to open PF_BLUETOOTH socket`.

On Debian or Ubuntu:

```bash
sudo apt update
sudo apt install -y bluez
sudo systemctl enable --now bluetooth
```

Example Docker Compose configuration:

```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
      - /run/dbus:/run/dbus:ro
```

Then:

1. Verify that the host adapter and BlueZ service are available:

   ```bash
   sudo systemctl enable --now bluetooth
   bluetoothctl list
   ```

2. Recreate the Home Assistant container.
3. Install the integration through HACS.
4. Select Local or Automatic.
5. Test wake-up.

For a quick container-side check:

```bash
docker exec homeassistant test -S /run/dbus/system_bus_socket
docker exec homeassistant python -c \
  'import socket; s=socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI); print("Bluetooth HCI socket: ok"); s.close()'
```

Do not start another `bluetoothd` inside the Home Assistant container. The
container must use the Docker host's BlueZ service. A missing D-Bus mount is
reported with guidance mentioning `/run/dbus:/run/dbus:ro`; a permission
failure mentions `NET_ADMIN` and `NET_RAW`.

### Backend 3: ESP32

This backend presses a dedicated Home Assistant `button` entity, for example:

```text
button.xgimi_projector_wakeup
```

The button must be provided by a separate BLE-capable ESP32 running custom
ESPHome firmware that transmits this projector's token. Keep the ESP32 within
BLE range of the projector. A stock ESPHome Bluetooth Proxy cannot transmit an
arbitrary XGIMI manufacturer advertisement.

Setup:

1. Create or edit an ESPHome device.
2. Copy [`assets/esphome-xgimi-wake.yaml`](assets/esphome-xgimi-wake.yaml),
   replace its placeholder token bytes, and install the firmware.
3. Add the ESPHome device to Home Assistant and verify the
   XGIMI Projector Wakeup button.
4. Configure XGIMI, select ESP32, choose that button, and test wake-up.

The example includes a Bluetooth Proxy as well as the custom advertiser and
contains detailed comments for the wake button, token bytes, and optional scan
pause/resume. Proxy plus advertising uses additional BLE RAM and radio time.

For ESPHome raw manufacturer data, include the little-endian manufacturer ID:

```text
0x46, 0x00, <token bytes>
```

Local BlueZ receives ID `0x0046` and the token payload separately.

## Finding the BLE token

Home Assistant's built-in Bluetooth Advertisement Monitor can capture the
projector remote's wake packet:

1. Open Settings → Devices & services → Bluetooth → Configure →
   Advertisement Monitor, or use the
   [Bluetooth Advertisement Monitor shortcut](https://my.home-assistant.io/redirect/bluetooth_advertisement_monitor/).
2. Turn the projector off so the remote is not connected to it.
3. Press the remote's power button.
4. Find manufacturer-data key `70` (decimal `70` is hexadecimal `0x46`).
5. Copy its hexadecimal value only. Do not include the key itself.

Illustrative monitor value:

```text
51f55a6d78e450ffffff0000000b000d
```

For the local backend:

```text
Manufacturer ID: 0x0046
Payload: 51f55a6d78e450ffffff0000000b000d
```

BlueZ adds the little-endian manufacturer identifier. Do not prepend `46 00` to
the token entered in the integration.

For an ESPHome raw byte vector:

```text
46 00 51 f5 5a 6d 78 e4 50 ff ff ff 00 00 00 0b 00 0d
```

To convert a token, split the hexadecimal string into pairs and write each pair
as `0xNN`, separated by commas. The committed ESPHome example contains only
zero placeholders, never a device token.

## Remote commands

The integration creates one remote entity, such as `remote.living_room_xgimi`.

```yaml
action: remote.send_command
target:
  entity_id: remote.living_room_xgimi
data:
  command: volumeup
```

Common commands:

```text
play, pause, power, back, home, menu, right, left,
up, down, volumedown, volumeup, poweron, poweroff, volumemute
```

Model-dependent commands:

```text
autofocus, autofocus_new,
manual_focus_left, manual_focus_right,
motor_left_overstep, motor_left_start,
motor_right_overstep, motor_right_start, motor_stop,
shortcut_setting, choose_source, hibernate, xmusic
```

`poweron` uses the effective wake backend. Every other command continues to use
the existing UDP implementation.

## Troubleshooting

- Enable debug logging and wownload integration diagnostics.
- For Container, verify the host BlueZ service, `/run/dbus:/run/dbus:ro`,
  `NET_ADMIN`, and `NET_RAW`.
- For ESP32, verify the dedicated wake button—not merely a Bluetooth Proxy—is
  present and available.
- If LAN commands do not work, the projector may use native Android TV control.
  Consider Home Assistant's
  [Android TV Remote](https://www.home-assistant.io/integrations/androidtv_remote/)
  integration for those commands.

## Dashboard example

See [`assets/tv-card-example.yaml`](assets/tv-card-example.yaml) for an example
using [tv-card](https://github.com/marrobHD/tv-card).

<img src="assets/tv_card.png" width="200" height="220" alt="TV card example">
