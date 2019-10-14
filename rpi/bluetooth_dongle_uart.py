from imports import *
import time
from datetime import datetime
import serial
import random
import os
import threading

from io import BytesIO
from PIL import Image

"""
Version
"""
MAJOR_VERSION = 1
MINOR_VERSION = 0



"""
HOST commands
"""
# 0xA0 : ack command to tx site
HOST_CMD_ACK = 0xA0

# 0xB0 - 0xBF : BLE commands
HOST_CMD_BLE_STATS = 0xB0
HOST_CMD_BLE_SCAN_START = 0xB1
HOST_CMD_BLE_SCAN_STOP = 0xB2
HOST_CMD_BLE_CONNECT = 0xB3
HOST_CMD_BLE_DISCONNECT = 0xB4

# 0xC0 - 0xCF : camera commands
HOST_CMD_CAM_STATS = 0xC0
HOST_CMD_CAM_CAPTURE = 0xC1
HOST_CMD_CAM_START_STREAM = 0xC2
HOST_CMD_CAM_STOP_STREAM = 0xC3
HOST_CMD_CAM_CHANGE_RESOLUTION = 0xC4
HOST_CMD_CAM_CHANGE_PHY = 0xC5
HOST_CMD_CAM_BLE_PARAMS_INFO = 0xC6
HOST_CMD_CAM_CAMERA_DATA_LENGTH = 0xC7
HOST_CMD_CAM_CAMERA_DATA_READY = 0xC8
HOST_CMD_CAM_CAMERA_DATA = 0xC9
HOST_CMD_CAM_DATA_UPLOAD = 0xCA
HOST_CMD_CAM_CAMERA_DFU = 0xCE
HOST_CMD_CAM_CAMERA_REBOOT = 0xCF

# 0xD0 - 0xDF : dongle commands
HOST_CMD_DNG_BLE_STATS = 0xD0
HOST_CMD_DNG_REBOOT = 0xD1

# 0xFF : engineering commands
HOST_CMD_ENG_LOCAL_ECHO = 0xF0
HOST_CMD_ENG_END_OP_CODE = 0xFE

"""
HOST response code
"""
HOST_CMD_RSP_ACK = 0x00
HOST_CMD_RSP_NACK = 0x01
HOST_CMD_RSP_BLE_IS_NOT_CONNECTED = 0xE0
HOST_CMD_RSP_CAMERA_IS_NOT_READY = 0xE1
HOST_CMD_RSP_INVALID_COMMAND = 0xE2
HOST_CMD_RSP_INVALID_STATE = 0xE3

"""
Commands Definition
    - Index 0 = command
    - Index 1 = payload length
    - Index 2 and after = payload
"""
command = \
{
    'camera_stats'   : bytearray([HOST_CMD_CAM_STATS,         0x01, HOST_CMD_ENG_END_OP_CODE]),
    'camera_reboot'  : bytearray([HOST_CMD_CAM_CAMERA_REBOOT, 0x01, HOST_CMD_ENG_END_OP_CODE]),
    'single_capture' : bytearray([HOST_CMD_CAM_CAPTURE,       0x01, HOST_CMD_ENG_END_OP_CODE]),
    'image_upload'   : bytearray([HOST_CMD_CAM_DATA_UPLOAD,   0x01, HOST_CMD_ENG_END_OP_CODE]),
    'ble_stats'      : bytearray([HOST_CMD_BLE_STATS,         0x01, HOST_CMD_ENG_END_OP_CODE]),
    'ble_scan_start' : bytearray([HOST_CMD_BLE_SCAN_START,    0x01, HOST_CMD_ENG_END_OP_CODE]),
    'ble_scan_stop'  : bytearray([HOST_CMD_BLE_SCAN_STOP,     0x01, HOST_CMD_ENG_END_OP_CODE]),
    'ble_connect'    : bytearray([HOST_CMD_BLE_CONNECT,       0x01, HOST_CMD_ENG_END_OP_CODE]),
    'ble_disconnect' : bytearray([HOST_CMD_BLE_DISCONNECT,    0x03, 0x3C, 0x00, HOST_CMD_ENG_END_OP_CODE]),
    'dongle_reboot'  : bytearray([HOST_CMD_DNG_REBOOT,        0x01, HOST_CMD_ENG_END_OP_CODE]),
}

"""
BLE stats
    - Index 2 = BLE Stats
    - Index 3~8 = BLE Connected device address
"""
BLE_STATS_IDLE = 0
BLE_STATS_SCAN = 1
BLE_STATS_CONN = 2
BLE_STATS_SIZE = 8 # stats (1) + bda (6) + end_of_op_code (1)

"""
Interface
"""
ENABLE_UART_LOG = 0x0

class DeviceInfo():
    def __init__(self, device_addr):
        self.device_id = device_addr
        self.last_timestamp = ""
        self.last_stream = None
        self.has_registered = False

    def get_last_stream(self):
        return self.last_stream

    def set_last_stream(self, stream):
        self.last_stream = stream

class BluetoothDongleUart(threading.Thread):
    def __init__(self, sleep_time=60, log_level='DEBUG'):
        """
        UART configuration
        """
        threading.Thread.__init__(self)
        ## init logger
        loggerfactory = LoggerFactory(__name__, level=log_level)
        loggerfactory.add_handler(handler='CONSOLE', format=DEFAULT_LOG_FORMAT, level=log_level)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME, level=log_level)
        self._logger = loggerfactory.get_logger()

        self.device_camera = {}
        self.ble_scan_period_time_second = 300
        self.capture_period_time_second = sleep_time
        self.transmission_timeout_second = 30

        self.uart = serial.Serial()
        self.uart.port = self._parse_uart_port()
        self.uart.baudrate = 115200
        self.uart.bytesize = serial.EIGHTBITS    # number of bits per bytes
        self.uart.parity = serial.PARITY_NONE    # set parity check: no parity
        self.uart.stopbits = serial.STOPBITS_ONE # number of stop bits

        #uart.timeout = None            # block read
        self.uart.timeout = 1          # non-block read
        #uart.timeout = 2               # timeout block read
        self.uart.xonxoff = False      # disable software flow control
        self.uart.rtscts = False       # disable hardware (RTS/CTS) flow control
        self.uart.dsrdtr = False       # disable hardware (DSR/DTR) flow control
        self.uart.writeTimeout = 2     # timeout for write

    def _parse_uart_port(self):
        ports = [x for x in os.listdir('/dev') if x.find('tty.usbserial') != -1]
        if ports:
            return '/dev/' + ports[0]
        else:
            msg = 'uart port parsing error'
            self._logger.error(msg)
            raise ValueError(msg)

    def send_command(self, command):
        self.uart.write(command)

    def recv_command(self):
        response = bytearray()

        # command
        response += self.uart.read()

        # payload length
        length = self.uart.read()
        response += length

        # payload
        length = int.from_bytes(length, 'little')
        length -= 1 # remove end op code
        if length:
            response += self.uart.read(length)

        # end op code
        end_of_code = self.uart.read()
        response += end_of_code
        end_of_code = int.from_bytes(end_of_code, 'little')
        if end_of_code == HOST_CMD_ENG_END_OP_CODE:
            if ENABLE_UART_LOG:
                print('<- ' + str(response))
            return response
        else:
            if ENABLE_UART_LOG:
                print('recv_command: invalid end op code - 0x%02x' % end_of_code)
                #print('recv_command: ' + str(response))
            return None

    def ble_stats(self):
        ble_stats = BLE_STATS_IDLE
        dev_addrs = ''
        try:
            self.send_command(command['ble_stats'])
            response = self.recv_command()
            if response[0] == HOST_CMD_BLE_STATS and response[1] == BLE_STATS_SIZE:
                ble_stats = int(response[2])
                dev_addrs = ('%02x%02x%02x%02x%02x%02x' % (response[3],
                                                        response[4],
                                                        response[5],
                                                        response[6],
                                                        response[7],
                                                        response[8]))
        except:
            self._logger.debug('ble_is_ready: communication error!!')
            return None, None

        if ble_stats == BLE_STATS_IDLE:
            self._logger.debug('ble_stats: idle')
        elif ble_stats == BLE_STATS_SCAN:
            self._logger.debug('ble_stats: scanning')
        else:
            self._logger.debug('ble_stats: connected to camera_' + dev_addrs)
        return ble_stats, dev_addrs

    def ble_scan_onoff(self, onoff):
        try:
            if onoff:
                self.send_command(command['ble_scan_start'])
            else:
                self.send_command(command['ble_scan_stop'])

            response = self.recv_command()
            if response[0] == HOST_CMD_ACK and response[2] == HOST_CMD_RSP_ACK:
                if onoff:
                    self._logger.debug('ble_scan_onoff: scanning')
                else:
                    self._logger.debug('ble_scan_onoff: idle')

                return True
        except:
            self._logger.debug('ble_scan_onoff: communication error!!')

        return False

    def ble_disconnect(self, adv_delay_sec):
        try:
            # ble disconnect with 2 bytes of adv delay time in seconds
            command['ble_disconnect'][2] = (adv_delay_sec & 0xff)
            command['ble_disconnect'][3] = ((adv_delay_sec >> 8) & 0xff)
            self.send_command(command['ble_disconnect'])
            response = self.recv_command()
            if response[0] == HOST_CMD_ACK and response[2] == HOST_CMD_RSP_ACK:
                self._logger.debug('ble_disconnect: setup advertising after %u seconds' % adv_delay_sec)
            else:
                self._logger.debug('ble_disconnect: failed')
        except:
            self._logger.debug('ble_disconnect: communication error!!')
            return False

        return True

    def dongle_reboot(self):
        try:
            self.send_command(command['dongle_reboot'])
        except:
            self._logger.debug('dongle_reboot: communication error!!')
            return

        self._logger.debug('dongle_reboot: ok')

    def dongle_flush(self):
        self.uart.flushInput()  # flush input buffer, discarding all its contents
        self.uart.flushOutput() # flush output buffer, aborting current output
                        # and discard all that is in buffer

    def camera_stats(self):
        try:
            self.send_command(command['camera_stats'])
            response = self.recv_command()
            if response[0] == HOST_CMD_ACK and response[2] == HOST_CMD_RSP_ACK:
                time.sleep(0.5)
                response = self.recv_command()
                if response[5]:
                    version = ('v%u.%u.%u' % (response[2], \
                                            response[3], \
                                            response[4]))
                    fmt = 'jpg'
                    if response[6] != 1:
                        fmt = str(response[6])
                    res = '640x480'
                    if response[7] != 2:
                        res = str(response[7])

                    self._logger.debug('camera stats: %s / %s / %s' % (version, fmt, res))
                    return True, version, response[6], response[7]
            else:
                self._logger.debug('camera_stats: nack')
                return False, None, None, None
        except:
            self._logger.debug('camera_stats: communication error!!')
            return False, None, None, None

        self._logger.debug('camera_stats: not ready')
        return False, None, None, None

    def camera_reboot(self):
        try:
            self.send_command(command['camera_reboot'])
            response = self.recv_command()
            if response[0] == HOST_CMD_ACK and response[2] == HOST_CMD_RSP_ACK:
                self._logger.debug('camera_reboot: ok')
                return True
            else:
                self._logger.debug('camera_reboot: failed')
                return False
        except:
            self._logger.debug('camera_reboot: communication error!!')

        return False

    def single_capture(self, wait_for_length):
        self._logger.debug("single_capture")
        total_image_size = 0
        try:
            self.send_command(command['single_capture'])
            self.recv_command()
            # wait to recv camera data length
            time.sleep(wait_for_length)
            # recv image size
            response = self.recv_command()
            if response[0] == HOST_CMD_CAM_CAMERA_DATA_LENGTH:
                total_image_size = (response[2]) | \
                                (response[3] << 8) | \
                                (response[4] << 16)
        except:
            self._logger.debug('single_capture: communication error!!')
        return total_image_size

    def camera_data_ready(self, timeout_s):
        # start time
        time_start = datetime.utcnow().timestamp()

        try:
            # command
            wait = True
            while wait:
                command = self.uart.read()
                command = int.from_bytes(command, 'little')
                if command == HOST_CMD_CAM_CAMERA_DATA_READY:
                    wait = False
                    self._logger.debug('image data is ready to dump')
                else:
                    time_now = datetime.utcnow().timestamp()
                    time_delta = time_now - time_start
                    self._logger.debug('waiting for image data ready... %u/%u' % (time_delta, timeout_s))
                    if time_delta > timeout_s:
                        self._logger.debug('waiting for image data ready timeout!!')
                        return False

            # payload length
            length = self.uart.read(1)
            length = int.from_bytes(length, 'little')

            # payload
            length -= 1 # remove end op code
            if length:
                self.uart.read(length)

            # end op code
            end_of_code = self.uart.read(1)
            end_of_code = int.from_bytes(end_of_code, 'little')
            if end_of_code != HOST_CMD_ENG_END_OP_CODE:
                self._logger.debug('wrong end of code: 0x%02x' % end_of_code)
                return False
        except:
            self._logger.debug('camera_data_ready: communication error!!')
            return False

        # done
        return True

    def camera_data_upload(self):
        try:
            self.send_command(command['image_upload'])
            response = self.recv_command()
            if response[0] == HOST_CMD_ACK and response[2] == HOST_CMD_RSP_ACK:
                self._logger.debug('camera_data_upload: ack')
                return True
        except:
            self._logger.debug('camera_data_upload: communication error!!')

        return False

    def dump_camera_data(self, image_size, timeout_s):
        # start time
        time_start = datetime.utcnow().timestamp()

        image_data = bytearray()
        recv_image_size = 0
        while recv_image_size < image_size:
            try:
                # command - must wait for the first command byte
                wait = True
                while wait:
                    command = self.uart.read()
                    command = int.from_bytes(command, 'little')
                    if command == HOST_CMD_CAM_CAMERA_DATA:
                        wait = False
                    else:
                        self._logger.debug('waiting for header... 0x%02x' % command)

                # payload length
                length = self.uart.read(1)
                length = int.from_bytes(length, 'little')

                # payload
                length -= 1 # remove end op code
                if length:
                    image_data += self.uart.read(length)

                # end op code
                end_of_code = self.uart.read(1)
                end_of_code = int.from_bytes(end_of_code, 'little')
                if end_of_code != HOST_CMD_ENG_END_OP_CODE:
                    self._logger.debug('wrong end of code: 0x%02x' % end_of_code)
                    return None
            except:
                self._logger.debug('dump_camera_data: communication error!!')
                return None
            finally:
                recv_image_size += length

            time_now = datetime.utcnow().timestamp()
            time_delta = time_now - time_start
            if time_delta > timeout_s:
                self._logger.debug('dump_camera_data: time expire!!')
                return None

        self._logger.debug('dump_camera_data: recv= %lu' % recv_image_size)
        return image_data



    def save_camera_image(self, camera_addr, camera_data):
        try:
            curr_time = datetime.now()
            file_name = ('camera_%s_%s.jpg' % (camera_addr, curr_time.strftime('%Y%m%d_%H.%M.%S')))
            f = open(file_name, 'wb')
            f.write(camera_data)
            f.close()
            self._logger.debug('output to %s' % file_name)
        except:
            self._logger.debug('save_camera_image: output jpg file error!!')

        return True

    def run(self):
        # open the port
        try:
            self.uart.open()
        except Exception as e:
            self._logger.error("error open serial port")
            raise e
        
        self.dongle_flush()

        while True:
            # wait for BLE connection
            conn_counts = 0
            stats = BLE_STATS_IDLE
            addr = ''
            
            ## scan to find cameras
            while stats != BLE_STATS_CONN:
                # get ble stats
                time.sleep(1)
                stats, addr = self.ble_stats()
                if stats == BLE_STATS_IDLE:
                    # start scanning
                    self.ble_scan_onoff(True)
                else:
                    # in scanning
                    conn_counts += 1
                    if conn_counts >= self.ble_scan_period_time_second:
                        # something is wrong due to not connected out of capture period time
                        # reboot dongle
                        conn_counts = 0
                        self.dongle_reboot()
                        time.sleep(5)

            # save camera device address
            if addr in self.device_camera:
                self._logger.debug('connected to camera %s' % addr)
            else:
                self.device_camera[addr] = DeviceInfo(addr)
                self._logger.debug('connected to new camera %s' % addr)

            time.sleep(1)
            retry = 3
            ready, version, fmt, resolution = self.camera_stats()

            ## s2: wait for camera ready
            while retry and not ready:
                time.sleep(1)
                ready, version, fmt, resolution = self.camera_stats()
                retry -= 1

            # check camera stats
            if ready:
                # capture image
                time.sleep(0.1)
                image_size = self.single_capture(3)
                self._logger.debug('single captured: %lu bytes' % image_size)
                if image_size:
                    # wait for data ready
                    if self.camera_data_ready(self.transmission_timeout_second):
                        # drop BLE connection
                        time.sleep(0.1)
                        self.ble_disconnect(self.capture_period_time_second)
                        time.sleep(0.1)
                        time.sleep(1)

                        # wait for BLE disconnected
                        dis_counts = 0
                        reboot = False
                        while stats != BLE_STATS_IDLE:
                            time.sleep(1)
                            stats, not_used = self.ble_stats()
                            # try to disconnect
                            dis_counts += 1
                            if dis_counts > 3:
                                self.ble_disconnect(self.capture_period_time_second)
                                time.sleep(0.1)
                            # still can't drop ble connection
                            # reboot dongle to force ble disconnected
                            if dis_counts > 6:
                                self._logger.debug('reboot to force ble disconnected')
                                reboot = True
                                self.dongle_reboot()
                                time.sleep(5)

                        if not reboot:
                            # request to upload camera data
                            self.camera_data_upload()

                            # start to dump camera data
                            self._logger.debug('start image data uploading')
                            image_data = self.dump_camera_data(image_size, self.transmission_timeout_second)
                            last_ts = str(int(datetime.timestamp(datetime.now())))
                            if image_data == None:
                                self._logger.debug('invalid camera data')
                                device_info = self.device_camera[addr]
                                ## heartbeat data
                                device_info.last_timestamp = last_ts
                                device_info.set_last_stream(None)
                            else:
                                #self.save_camera_image(addr, image_data)
                                device_info = self.device_camera[addr]
                                ## heartbeat data
                                device_info.last_timestamp = last_ts
                                device_info.set_last_stream(image_data)
                                self._logger.debug('completed')
                    else:
                        self._logger.debug('image data is not available')
                        # self reboot
                        time.sleep(0.1)
                        self.dongle_reboot()
                        # wait for BLE disconnect - dirty disconnected
                        self._logger.debug('waiting for BLE disconnected')
                        time.sleep(10)
                        self._logger.debug('done')
            else:
                self._logger.debug('camera is not ready to use!!')
                self.camera_reboot()

            # wait for next session
            time.sleep(1)

    def capture(self, device=None):
        if device is None:
            info = []
            for device_info in self.device_camera.values():
                info.append(
                    {'device_id': device_info.device_id,
                     'last_timestamp': device_info.last_timestamp,
                     'last_stream': device_info.get_last_stream(),
                     'has_registered': device_info.has_registered})

            return info
        else:
            device_info = self.device_camera[device]
            info = [{'device_id': device_info.device_id,
                     'last_timestamp': device_info.last_timestamp,
                     'last_stream': device_info.get_last_stream(),
                     'has_registered': device_info.has_registered}]
    
    def set_registered(self, device_id):
        if device_id in self.device_camera:
            info = self.device_camera[device_id]
            info.has_registered = True

    def flush_cache(self, device=None):
        if device is None:
            for device_info in self.device_camera.values():
                device_info.set_last_stream(None)
        else:
            device_info = self.device_camera[device]
            if device_info:
                device_info.set_last_stream(None)

if __name__ == "__main__":
    uart = BluetoothDongleUart()
    uart.start()
    time.sleep(10)
    while True:
        info = uart.capture()
        if info:
            device = info[0]
            name = device['device_id']
            ts = device['last_timestamp']
            stream = device['last_stream']
            if stream:
                image = Image.open(BytesIO(stream))
                file_path = name + '_' + ts + '.jpg'
                image.save(file_path)
            uart.flush_cache()
        time.sleep(10)
