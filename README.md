# Xgimi-4-Home-Assistant
XGIMI integration for home assistant

## Install
1. Copy whole folder `xgimi` into home assistant `custom_components`  
2. Restart home assistant  
3. Add following lines to `configuration.yaml`  
    ```yaml
    remote:
    - platform: xgimi
      name: z6x  # can be changed with any name you like
      host: 192.168.0.115  # your xgimi projector IP
      token: "12D7C7899B9F80FFFFFF3043524B544D"  # BLE manufacture data
    ```
4. Restart home assistant

## How to use
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
up, down, volumedown, volumeup, poweron, poweroff, volumemute
```
### Dashboard example
See [tv-card-example.yaml](tv-card-example.yaml) for a dashboard example using [tv-card](https://github.com/marrobHD/tv-card)

## About Power-On with ble manufacture data
The integration communicates with xigimi projector by UDP except for the **poweron** command. Once the projector is powered off, the only way to wake it up is sending a special ble advertisement. Such a ble advertisement contains a special token called `manufacture data`. The manufacture data seems to be different for each model. Please go through issue [#5](https://github.com/manymuch/Xgimi-4-Home-Assistant/issues/5) for better understanding and how you can get manufacture data of your projector.  
The **poweron** command is in beta mode, it is not guaranteed to work every time. Please let me know if you have any issue with it.

## TODO
- setup through UI
- auto discovery  
- media player entity
- more command support  


This integration is in very early stage, contributions and suggestions are welcome!
