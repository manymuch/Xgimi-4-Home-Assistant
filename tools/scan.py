import asyncio
import bleak

async def print_device_info(device):
    manufacturer_data = device.metadata.get("manufacturer_data", {})
    if manufacturer_data:
        for manufacturer_code, data in manufacturer_data.items():
            if manufacturer_code != 70:
                continue
            print(f"Device name: {device.name}, Address: {device.address}")
            hex_code = format(manufacturer_code, '02X')
            hex_data = ''.join(format(byte, '02X') for byte in data)
            print(f"Manufacturer 0x{hex_code}\nData 0x{hex_data}")

async def scan_for_ble_devices():
    devices = await bleak.discover()
    if devices:
        print("Discovered BLE device(s):")
        for device in devices:
            await print_device_info(device)
    else:
        print("No BLE devices found nearby.")

async def loop_scan():
    while True:
        await scan_for_ble_devices()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(loop_scan())
    #loop.run_until_complete(scan_for_ble_devices())
