import asyncio
from bluez_peripheral.util import get_message_bus
from bluez_peripheral.advert import Advertisement


async def async_ble_power_on(manufacturer_data: str, company_id: int = 0x0046, service_uuid: str = "1812"):
    bus = await get_message_bus()
    advert = Advertisement(
        localName="Bluetooth 4.0 RC",
        serviceUUIDs=[service_uuid],
        manufacturerData={company_id: bytes.fromhex(manufacturer_data)},
        timeout=10000,
        duration=1000,
        appearance=961,
    )
    await advert.register(bus)
    await asyncio.sleep(10)

if __name__ == "__main__":
    manufacturer_data = "12D7C7899B9F80FFFFFF3043524B544D"
    asyncio.run(async_ble_power_on(manufacturer_data))
