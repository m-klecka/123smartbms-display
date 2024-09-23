import serial_asyncio  # type: ignore
import time
import asyncio
import aiohttp  # type: ignore
from aiohttp import web  # type: ignore
import os

BMS_COMM_GAP = 300
BMS_COMM_TIMEOUT = 10000
BMS_COMM_BLOCK_SIZE = 58

class BMS(object):
    def __init__(self, loop, port):
        self._loop = loop
        self._port = port
        self._serial_loop_task = None
        self._last_received = 0
        self._pack_voltage = 0
        self._charge_current = 0
        self._discharge_current = 0
        self._pack_current = 0
        self._soc = 0
        self._lowest_cell_voltage = 0
        self._lowest_cell_voltage_num = 0
        self._highest_cell_voltage = 0
        self._highest_cell_voltage_num = 0
        self._lowest_cell_temperature = 0
        self._lowest_cell_temperature_num = 0
        self._highest_cell_temperature = 0
        self._highest_cell_temperature_num = 0
        self._cell_count = 0
        self._cell_communication_error = 1
        self._allowed_to_charge = 0
        self._allowed_to_discharge = 0
        self._web_data = {}
        self._connected = False

    async def connect(self):
        while True:
            try:
                self._serial_loop_task = self._loop.create_task(self._serial_read(self._port))
                self._connected = True
                print(f"Connected to {self._port}")
                break
            except (PermissionError, FileNotFoundError) as e:
                print(f"Failed to open port {self._port}. Retrying in 5 seconds...")
                self._connected = False
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Unexpected error: {e}. Retrying in 5 seconds...")
                self._connected = False
                await asyncio.sleep(5)

    async def disconnect(self):
        if self._serial_loop_task:
            self._serial_loop_task.cancel()
            try:
                await self._serial_loop_task
            except asyncio.CancelledError:
                pass
        self._connected = False
        print(f"Disconnected from {self._port}")

    @property
    def data(self):
        return self._web_data

    @property
    def connection_status(self):
        return self._connected

    async def _serial_read(self, port):
        while True:
            try:
                print(f"Attempting to open port {port}...")
                reader, _ = await serial_asyncio.open_serial_connection(url=port, baudrate=9600)
                print(f"Port {port} opened successfully.")
                self._last_received = self._millis()
                bytes_received = 0
                buf = bytearray(BMS_COMM_BLOCK_SIZE)
                while True:
                    rx_byte = await reader.readexactly(1)
                    if self._millis() > self._last_received + BMS_COMM_GAP:
                        bytes_received = 0
                    self._last_received = self._millis()

                    if bytes_received < BMS_COMM_BLOCK_SIZE:
                        buf[bytes_received] = rx_byte[0]
                        bytes_received += 1

                    if bytes_received == BMS_COMM_BLOCK_SIZE:
                        bytes_received = 0
                        checksum = 0
                        for i in range(BMS_COMM_BLOCK_SIZE - 1):
                            checksum += buf[i]

                        received_checksum = buf[BMS_COMM_BLOCK_SIZE - 1]
                        if (checksum & 0xff) == received_checksum:
                            self._pack_voltage = self._decode_voltage(buf[0:3])
                            self._charge_current = self._decode_current(buf[3:6])
                            self._discharge_current = self._decode_current(buf[6:9])
                            self._pack_current = self._decode_current(buf[9:12])
                            self._soc = buf[40]
                            self._lowest_cell_voltage = self._decode_voltage(buf[12:14])
                            self._lowest_cell_voltage_num = buf[14]
                            self._highest_cell_voltage = self._decode_voltage(buf[15:17])
                            self._highest_cell_voltage_num = buf[17]
                            self._lowest_cell_temperature = self._decode_temperature(buf[18:20])
                            self._lowest_cell_temperature_num = buf[20]
                            self._highest_cell_temperature = self._decode_temperature(buf[21:23])
                            self._highest_cell_temperature_num = buf[23]
                            self._cell_count = buf[25]
                            self._cell_communication_error = True if (buf[30] & 0b00000100) else False
                            self._allowed_to_discharge = True if (buf[30] & 0b00000010) else False
                            self._allowed_to_charge = True if (buf[30] & 0b00000001) else False

                            self._web_data = {
                                'pack_voltage': self._pack_voltage,
                                'charge_current': self._charge_current,
                                'discharge_current': self._discharge_current,
                                'pack_current': self._pack_current,
                                'soc': self._soc,
                                'lowest_cell_voltage': self._lowest_cell_voltage,
                                'lowest_cell_voltage_num': self._lowest_cell_voltage_num,
                                'highest_cell_voltage': self._highest_cell_voltage,
                                'highest_cell_voltage_num': self._highest_cell_voltage_num,
                                'lowest_cell_temperature': self._lowest_cell_temperature,
                                'lowest_cell_temperature_num': self._lowest_cell_temperature_num,
                                'highest_cell_temperature': self._highest_cell_temperature,
                                'highest_cell_temperature_num': self._highest_cell_temperature_num,
                                'cell_count': self._cell_count,
                                'cell_communication_error': self._cell_communication_error,
                                'allowed_to_discharge': self._allowed_to_discharge,
                                'allowed_to_charge': self._allowed_to_charge,
                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                            }
            except (PermissionError, FileNotFoundError) as e:
                print(f"Serial port error: {e}. Reconnecting in 5 seconds...")
                await self.disconnect()
                await asyncio.sleep(5)  # Wait before retrying connection
                # Loop to attempt reconnecting
                while not self._connected:
                    await self.connect()
            except Exception as e:
                print(f"Unexpected error: {e}. Reconnecting in 5 seconds...")
                await self.disconnect()
                await asyncio.sleep(5)  # Wait before retrying connection
                # Loop to attempt reconnecting
                while not self._connected:
                    await self.connect()

    def _decode_current(self, raw_value):
        if raw_value[0] == ord('X'):
            return 0
        elif raw_value[0] == ord('-'):
            factor = -1
        else:
            factor = 1
        return factor * round(0.125 * int.from_bytes(raw_value[1:3], byteorder='big', signed=False), 1)

    def _decode_voltage(self, raw_value):
        voltage = int.from_bytes(raw_value, byteorder='big', signed=False)
        return round(0.005 * voltage, 2)

    def _decode_temperature(self, raw_value):
        return round(int.from_bytes(raw_value[0:2], byteorder='big', signed=False) * 0.857 - 232, 0)

    def _millis(self):
        return int(time.time() * 1000)

async def handle_status(request):
    if bms.connection_status:
        return web.json_response(bms.data)
    else:
        return web.json_response({
            'pack_voltage': '-',
            'charge_current': '-',
            'discharge_current': '-',
            'pack_current': '-',
            'soc': '-',
            'lowest_cell_voltage': '-',
            'lowest_cell_voltage_num': '-',
            'highest_cell_voltage': '-',
            'highest_cell_voltage_num': '-',
            'lowest_cell_temperature': '-',
            'lowest_cell_temperature_num': '-',
            'highest_cell_temperature': '-',
            'highest_cell_temperature_num': '-',
            'cell_count': '-',
            'cell_communication_error': '-',
            'allowed_to_discharge': '-',
            'allowed_to_charge': '-',
            'timestamp': '-'
        })

async def handle_connection_status(request):
    return web.json_response({'connected': bms.connection_status})

async def handle_index(request):
    with open('index.html', encoding='utf-8') as f:
        return web.Response(text=f.read(), content_type='text/html')

async def init_app():
    app = web.Application()
    app.router.add_get('/status', handle_status)
    app.router.add_get('/connection_status', handle_connection_status)
    app.router.add_get('/', handle_index)
    
    # Serve static files from the static directory
    static_dir = os.path.dirname(__file__)
    app.router.add_static('/static/', path=os.path.join(static_dir, 'static'), name='static')

    return app

async def main():
    loop = asyncio.get_event_loop()
    global bms
    bms = BMS(loop, '/dev/ttyUSB0')

    # Run web server
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8080)
    await site.start()
    
    # Start connection attempt
    await bms.connect()

    try:
        while True:
            await asyncio.sleep(1)  # Keep the connection open
    except asyncio.CancelledError:
        await bms.disconnect()
        print("Disconnected due to cancellation.")

if __name__ == "__main__":
    asyncio.run(main())
