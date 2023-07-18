# Xgimi-4-Home-Assistant
<img src="https://brands.home-assistant.io/xgimi/logo.png"  width="360" height="120">  
XGIMI integration for home assistant


  
## 📦Install
1. Copy whole folder `xgimi` into home assistant `custom_components`  
2. Restart home assistant  

## 🏗️Setup
Prepare the following:  
``host``: local IP of the projector, check the router or the setting in the projector's menu.  
``token``: BLE token to power on the projector.  

Try these tokens for the following model.  
If that doesn't work or couldn't find your projector in the table, see for more details.
|      model     	|               token              	|
|:--------------:	|:--------------------------------:	|
|       H1S      	| 0ED8822F811CBCFFFFFF3043524B544D 	|
|       H5      	| 4D4B17D86C27E0FFFFFF3043524B544D 	|
|       H3       	| D1497DBDA42360FFFFFF3043524B544D 	|
|       H3S      	| 39BCA0F7A3ADB4FFFFFF3043524B544D 	|
|    New Z4 Air 	| 0917B18FCB2222FFFFFF3043524b544D 	|
|       Z6X      	| 12D7C7899B9F80FFFFFF3043524B544D 	|
|      Halo+     	| 143FCB9335F278FFFFFF3043524B544D 	|
|      Elfin     	| 12D7C7899B9F80FFFFFF3043524B544D 	|
| Horizon Pro 4K 	| 1A7E0C743AEF18FFFFFF3043524B544D 	|




Choose a method to setup:
### Method A: manual setup
1. Add the following lines to your `configuration.yaml`:
    ```yaml
    remote:
    - platform: xgimi
        name: Z6X
        host: 192.168.0.115
        token: "12D7C7899B9F80FFFFFF3043524B544D"
    ```

### Method B: UI setup
1. Make sure your projector is **powered on** and connected to the same network as home assistant
2. Add new integration, search for xgimi
3. Enter your projector information, for example:
    ```bash
    name: z6x
    host: 192.168.0.115
    token: 12D7C7899B9F80FFFFFF3043524B544D
    ```

## 📺How to use
The integration setup up a remote entity: e.g. `remote.z6x`.  
Example usage of remote.send_command service:  
```yaml
service: remote.send_command
data:
    command: volumeup
target:
    entity_id: remote.z6x
```
Current support command:  
```
play, pause, power, back, home, menu, right, left
up, down, volumedown, volumeup,
poweron, poweroff, volumemute, autofocus
```

### Dashboard example
See [tv-card-example.yaml](assets/tv-card-example.yaml) for a dashboard example using [tv-card](https://github.com/marrobHD/tv-card)  
<img src="assets/tv_card.png"  width="200" height="220">


## About BLE token for Power-On

The integration communicates with xgimi projector by UDP using local IP except for the **poweron** command. Once the projector is powered off, the only way to wake it up is sending a special ble advertisement. Such a ble advertisement contains a special token called `manufacture data`. The manufacture data seems to be different for each model.  

Try the token in the table provided above, if no luck :-(, go through the following stet by step:  

1. Make sure you Home Assistant is running on a device with bluetooth support (e.g. RaspberryPi)  
    a. you can check by running ``bluetoothctl`` in the terminal.  
    b. If you are running Home Assistant with docker, make sure HA is accessible to the bluetooth, see [issue #12](https://github.com/manymuch/Xgimi-4-Home-Assistant/issues/12).
    c. Make sure the bluetooth signal  from HA host machine can reach the projector without blockage.  

2. If still no luck, let's make some debugging:  

    Use ``bluetoothctl`` in the terminal of HA host machine:  
    ```bash
    [bluetooth]# menu advertise
    [bluetooth]# uuids 0x1812
    [bluetooth]# manufacturer 0x46 0x7e 0x31 0xdb 0x31 0xb2 0x24 0x40 0xff 0xff 0xff 0x30 0x43 0x52 0x4b 0x54 0x4d
    [bluetooth]# back
    [bluetooth]# advertise on
    ```
    Adjust the the token after the manufacturer according to your projector's model.  
    The first ``0x46`` is the company code followed by the actual manufacturer token.  
    If that does not work either, let's continue

3. Sniffering the token of your own projector model  
a. Completely unplug the projector.  
b. Get an iOS device and install [Bluetooth Smart Scanner App](https://apps.apple.com/us/app/bluetooth-smart-scanner/id509978131).  
c. Use the [Bluetooth Smart Scanner App](https://apps.apple.com/us/app/bluetooth-smart-scanner/id509978131) to scan while keep pressing the power on button on the remote. Look for the new BLE advertisement, it may contain a name like ``Bluetooth RC 4.0``.  Find the BLE token in the advertisement.  
d. Now you can try this token using buetoothctl, or test it with an android device direclty.  

4. Test the token with an android device.
Use [EFR connect](https://play.google.com/store/apps/details?id=com.siliconlabs.bledemo&hl=en&pli=1) to simulate a ble advertisement.  See this [screenshot](https://i.stack.imgur.com/4HLQs.jpg) for how to setup an advertisement accordingly.  

### More Related threads about BLE token
* [issue #5](https://github.com/manymuch/Xgimi-4-Home-Assistant/issues/5)
* [stackoverflow question](https://stackoverflow.com/questions/69921353/how-can-i-clone-a-non-paired-ble-signal-from-a-remote-to-trigger-a-device/75551013#75551013)

## TODO
- auto discovery  
- media player entity   


This integration is still in early stage, contributions and suggestions are welcome!  
Please give me a star:star_struck: if you like it.
