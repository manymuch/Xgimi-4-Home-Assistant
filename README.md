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
up, down, volumedown, volumeup, poweroff, volumemute
```
### Dashboard example
See [tv-card-example.yaml](tv-card-example.yaml) for a dashboard example using [tv-card](https://github.com/marrobHD/tv-card)

## Limitation
There is no way to **power on** the xgimi projector through this integration.
The integration communicates with xigimi projector by UDP, once the projector is powered off, the only way to wake it up is using the bluetooth remote. However, I can not find any relevant threads about how to simulate the bluetooth remote.  

## TODO
- setup through UI
- auto discovery  
- media player entity
- more command support  
- publish a pyxgimi package


This integration is in very early stage, contributions and suggestions are welcome!
