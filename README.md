# Xgimi-4-Home-Assistant
<img src="https://brands.home-assistant.io/xgimi/logo.png"  width="360" height="120">  

XGIMI integration for home assistant.  
Please give me a star :star_struck: if you like it.  


## 📦Install
### Manually
1. Download the latest source code ``xgimi.zip`` from [Releases](https://github.com/manymuch/Xgimi-4-Home-Assistant/releases)  
2. Unzip and copy the folder `xgimi` into home assistant `custom_components`  
2. Restart home assistant  
### Via HACS
1. Install [HACS](https://hacs.xyz/) if you do not have that already
2. In the Home Assitant HACS Tab, click on the three dots at the top right
3. Choose `Custom repositories`
4. Paste `https://github.com/manymuch/Xgimi-4-Home-Assistant/` to the repository field, choose the `Integration` category and click `ADD`
5. Close the dialog
6. Disable the repository filter (hit `CLEAR` on the right of the `Filtering by Downloaded` text)
7. Type `Xgimi` to the Search bar and select `Xgimi Projector Remote`
8. Click `DOWNLOAD` on the bottom right
9. Click `DOWNLOAD` in the dialog that just appeared
10. Restart home assistant

## 🛜Get BLE token

The integration communicates with xgimi projector by UDP using local IP except for the **poweron** command. Once the projector is powered off, the only way to turn up is sending a special ble advertisement. Such a ble advertisement contains a special token called `manufacture data`. The `manufacture data` is **different for each device even for same model**.  


This token can be obtained using Home Assistant's built-in **Bluetooth Advertisement Monitor**.

### 1. Open the Bluetooth Advertisement Monitor

You can access the monitor directly from your Home Assistant instance:

👉 [Open Bluetooth Advertisement Monitor](https://my.home-assistant.io/redirect/bluetooth_advertisement_monitor/)

Alternatively, navigate manually:

1. Go to **Settings → Devices & Services → Bluetooth → Configure**.
2. Select **Advertisement Monitor**.

This view displays all Bluetooth Low Energy (BLE) advertisement packets detected by your Bluetooth adapter.

### 2. Identify the Xgimi Remote MAC Address

Because the BLE environment may contain dozens of nearby devices, it’s helpful to filter results by MAC address.

If you don’t know the remote’s MAC address:

1. Pair your Xgimi remote temporarily with an Android phone.

   1. To pair the remote, turn off the projector completely or go to another room and simultaneously press and hold the **Back** and **Home** buttons until the indicator light flashes.
   2. Look for a device with the name **“XGIMI RC”** or **“BLuetooth 4.0 RC”** and pair with it.
2. In the Bluetooth settings, open **Device details** to find the **MAC address**.
3. Note down the first three bytes (the prefix). For example, in many cases XGIMI remotes begin with `1C:`.
4. After that, pair the remote with the projector again.

You can later use this prefix to narrow down advertisements in the HA monitor.

### 3. Filter and Locate the Manufacturer Data

1. In the **Advertisement Monitor**, apply a **MAC prefix filter** (e.g., `1C:`) to reduce noise.
2. Turn off your projector so that the remote control does not automatically connect to it.
3. Press the **Power** button on the remote to send a special BLE advertisement frame.
4. Look for entries where the **Manufacturer data** field is populated and has an entry with ID: `70`. This data is a hexadecimal payload broadcast by the remote and contains the BLE token required by the integration.

Example frame data:

```json
{
"name": "BLuetooth 4.0 RC",
"address": "1C:XX:XX:XX:XX:XX",
"rssi": -66,
"manufacturer_data": {
    "13": "383800000001",
    "70": "51f55a6d78e450ffffff0000000b000d"
},
"service_data": {},
"service_uuids": [
    "00001812-0000-1000-8000-00805f9b34fb"
],
"source": "30:24:XX:XX:XX:XX",
"connectable": true,
"time": 1761087659.0729098,
"tx_power": null,
"raw": "0000000000000c0000000f0f000000000e0000000000000000000d000000"
}
```

Copy the full value from the manufacturer data with ID `70` — this is the token required for integration configuration. In this example:
``51f55a6d78e450ffffff0000000b000d``.


## 🏗️Setup

1. Prepare the following:  
    * ``host``: local IP of the projector, check the router or the setting in the projector's menu.  (For all commands via LAN: poweroff, volume, etc.)  
    * ``token``: BLE token to power on the projector.  (For poweron command only, via bluetooth signals)

2. Make sure your projector is **powered on** and can be reached via LAN by home assistant.
3. Add new integration, search for xgimi
4. Enter your projector information, for example:
    ```bash
    name: z6x
    host: 192.168.0.115
    token: 51F55A6D78E450FFFFFF0000000B000D
    ```

## 📺How to use
The integration setup up a remote entity: e.g. `remote.z6x`.  
Example usage of remote.send_command service:  
```yaml
action: remote.send_command
data:
    command: volumeup
target:
    entity_id: remote.z6x
```
Available commands:  
The below commands work for all models:  
```
play, pause, power, back, home, menu, right, left,
up, down, volumedown, volumeup,
poweron, poweroff, volumemute
```
The below commands may only work for some models, you can have a try and good luck :-)  
```
autofocus, autofocus_new,
manual_focus_left, manual_focus_right,
motor_left_overstep, motor_left_start,
motor_right_overstep, motor_right_start, motor_stop,
shortcut_setting, choose_source, hibernate, xmusic
```

### Dashboard example
See [tv-card-example.yaml](assets/tv-card-example.yaml) for a dashboard example using [tv-card](https://github.com/marrobHD/tv-card)  
<img src="assets/tv_card.png"  width="200" height="220"> 


### Troubleshoot

1. If you are running Home Assistant with docker, make sure HA is accessible to the bluetooth, see [issue #12](https://github.com/manymuch/Xgimi-4-Home-Assistant/issues/12).  
2. Make sure the bluetooth signal from HA host machine can reach the projector without blockage.  

### More Related threads about BLE token

* [issue #5](https://github.com/manymuch/Xgimi-4-Home-Assistant/issues/5)
* [issue #31](https://github.com/manymuch/Xgimi-4-Home-Assistant/issues/31)
* [issue #54](https://github.com/manymuch/Xgimi-4-Home-Assistant/issues/54) Thanks @mik-laj for contributing usage of advertisement monitor in HA. 
* [stackoverflow discussion](https://stackoverflow.com/questions/69921353/how-can-i-clone-a-non-paired-ble-signal-from-a-remote-to-trigger-a-device/75551013#75551013)

## TODO
- auto discovery  
- media player entity   


Contributions and suggestions are welcome!  
Please give me a star :star_struck: if you like it.
