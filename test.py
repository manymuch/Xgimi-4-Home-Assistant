import asyncudp
import asyncio
from time import sleep

ip = "192.168.0.116"
command_port = 16735
advance_port = 16750
alive_port = 554


async def main(idx):
    msg = f"KEYPRESSES:{idx}"
    remote_addr = (ip, command_port)
    sock = await asyncudp.create_socket(remote_addr=remote_addr)
    sock.sendto(msg.encode("utf-8"))
    print(await sock.recvfrom())
    sock.close()

for idx in range(0, 30):
    print(f"Sending {idx}")
    asyncio.run(main(idx))
    sleep(1)
