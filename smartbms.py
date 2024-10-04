import serial_asyncio
import time
from flask import Flask, jsonify
import asyncio

app = Flask(__name__)

bms_data = {}

class BMS:
    def __init__(self, loop, port):
        self._loop = loop
        self._port = port
        self._serial_loop_task = None
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

    async def connect(self):
        self._serial_loop_task = self._loop.create_task(self._serial_read(self._port))
    
    async def disconnect(self):
        self._serial_loop_task.cancel()

    async def _serial_read(self, port):
        reader, _ = await serial_asyncio.open_serial_connection(url=port, baudrate=9600)
        buf = bytearray(58)
        while True:
            rx_byte = await reader.readexactly(1)
            buf.pop(0)
            buf.append(rx_byte[0])

            if len(buf) == 58:
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
                
                bms_data.update({
                    "pack_voltage": self._pack_voltage,
                    "charge_current": self._charge_current,
                    "discharge_current": self._discharge_current,
                    "pack_current": self._pack_current,
                    "soc": self._soc,
                    "lowest_cell_voltage": self._lowest_cell_voltage,
                    "lowest_cell_voltage_num": self._lowest_cell_voltage_num,
                    "highest_cell_voltage": self._highest_cell_voltage,
                    "highest_cell_voltage_num": self._highest_cell_voltage_num,
                    "lowest_cell_temperature": self._lowest_cell_temperature,
                    "lowest_cell_temperature_num": self._lowest_cell_temperature_num,
                    "highest_cell_temperature": self._highest_cell_temperature,
                    "highest_cell_temperature_num": self._highest_cell_temperature_num,
                    "cell_count": self._cell_count,
                    "cell_communication_error": self._cell_communication_error,
                    "allowed_to_charge": self._allowed_to_charge,
                    "allowed_to_discharge": self._allowed_to_discharge
                })

    def _decode_voltage(self, raw_value):
        voltage = int.from_bytes(raw_value, byteorder='big', signed=False)
        return round(0.005 * voltage, 2)

    def _decode_current(self, raw_value):
        if raw_value[0] == ord('X'):
            return 0
        elif raw_value[0] == ord('-'):
            factor = -1
        else:
            factor = 1
        return factor * round(0.125 * int.from_bytes(raw_value[1:3], byteorder='big', signed=False), 1)

    def _decode_temperature(self, raw_value):
        return round(int.from_bytes(raw_value[0:2], byteorder='big', signed=False) * 0.857 - 232, 0)

@app.route('/data', methods=['GET'])
def get_bms_data():
    return jsonify(bms_data)

async def main(loop, port):
    bms = BMS(loop, port)
    await bms.connect()
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    port = input("Zadejte port pro připojení k BMS: ")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop, port))
