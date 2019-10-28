#!/usr/bin/python

import time
import datetime
import serial
import random

"""
Version
"""
MAJOR_VERSION = 1
MINOR_VERSION = 0

"""
UART configuration
"""
uart = serial.Serial()
#uart.port = "/dev/tty.usbmodem0006834899451"
#uart.port = "/dev/tty.wchusbserial14120"
#uart.port = "/dev/tty.usbserial-A505FPEX"
uart.port = "/dev/tty.usbmodem0006833591721"
uart.baudrate = 115200
uart.bytesize = serial.EIGHTBITS    # number of bits per bytes
uart.parity = serial.PARITY_NONE    # set parity check: no parity
uart.stopbits = serial.STOPBITS_ONE # number of stop bits
#uart.timeout = None      # block read
uart.timeout = 1          # non-block read
#uart.timeout = 2         # timeout block read
uart.xonxoff = False      # disable software flow control
uart.rtscts = False       # disable hardware (RTS/CTS) flow control
uart.dsrdtr = False       # disable hardware (DSR/DTR) flow control
uart.writeTimeout = 2     # timeout for write

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
Variables
"""
device_camera = []
ble_scan_period_time_second = 300
capture_period_time_second = 60

transmission_timeout_second = 30

"""
Interface
"""
ENABLE_UART_LOG = 0x0

def send_command(uart, command):
    uart.write(command)
    if ENABLE_UART_LOG:
        print('-> ' + str(command))

def recv_command(uart):
    response = bytearray()

    # command
    response += uart.read()

    # payload length
    length = uart.read()
    response += length

    # payload
    length = int.from_bytes(length, 'little')
    length -= 1 # remove end op code
    if length:
        response += uart.read(length)

    # end op code
    end_of_code = uart.read()
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

def __print_log__(str):
    temp = ('%s %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), str))
    print(temp)

def ble_stats(uart):
    ble_stats = BLE_STATS_IDLE
    dev_addrs = ''
    try:
        send_command(uart, command['ble_stats'])
        response = recv_command(uart)
        if response[0] == HOST_CMD_BLE_STATS and response[1] == BLE_STATS_SIZE:
            ble_stats = int(response[2])
            dev_addrs = ('%02x%02x%02x%02x%02x%02x' % (response[3],
                                                       response[4],
                                                       response[5],
                                                       response[6],
                                                       response[7],
                                                       response[8]))
    except:
        __print_log__('ble_is_ready: communication error!!')
        return None, None

    if ble_stats == BLE_STATS_IDLE:
        __print_log__('ble_stats: idle')
    elif ble_stats == BLE_STATS_SCAN:
        __print_log__('ble_stats: scanning')
    else:
        __print_log__('ble_stats: connected to camera_' + dev_addrs)
    return ble_stats, dev_addrs

def ble_scan_onoff(uart, onoff):
    try:
        if onoff:
            send_command(uart, command['ble_scan_start'])
        else:
            send_command(uart, command['ble_scan_stop'])

        response = recv_command(uart)
        if response[0] == HOST_CMD_ACK and response[2] == HOST_CMD_RSP_ACK:
            if onoff:
                __print_log__('ble_scan_onoff: scanning')
            else:
                __print_log__('ble_scan_onoff: idle')

            return True
    except:
        __print_log__('ble_scan_onoff: communication error!!')

    return False

def ble_disconnect(uart, adv_delay_sec):
    try:
        # ble disconnect with 2 bytes of adv delay time in seconds
        command['ble_disconnect'][2] = (adv_delay_sec & 0xff)
        command['ble_disconnect'][3] = ((adv_delay_sec >> 8) & 0xff)
        send_command(uart, command['ble_disconnect'])
        response = recv_command(uart)
        if response[0] == HOST_CMD_ACK and response[2] == HOST_CMD_RSP_ACK:
            __print_log__('ble_disconnect: setup advertising after %u seconds' % adv_delay_sec)
        else:
            __print_log__('ble_disconnect: failed')
    except:
        __print_log__('ble_disconnect: communication error!!')
        return False

    return True

def camera_stats(uart):
    try:
        send_command(uart, command['camera_stats'])
        response = recv_command(uart)
        if response[0] == HOST_CMD_ACK and response[2] == HOST_CMD_RSP_ACK:
            time.sleep(0.5)
            response = recv_command(uart)
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

                __print_log__('camera stats: %s / %s / %s' % (version, fmt, res))
                return True, version, response[6], response[7]
        else:
            __print_log__('camera_stats: nack')
            return False, None, None, None
    except:
        __print_log__('camera_stats: communication error!!')
        return False, None, None, None

    __print_log__('camera_stats: not ready')
    return False, None, None, None

def camera_reboot(uart):
    try:
        send_command(uart, command['camera_reboot'])
        response = recv_command(uart)
        if response[0] == HOST_CMD_ACK and response[2] == HOST_CMD_RSP_ACK:
            __print_log__('camera_reboot: ok')
            return True
        else:
            __print_log__('camera_reboot: failed')
            return False
    except:
        __print_log__('camera_reboot: communication error!!')

    return False

def single_capture(uart, wait_for_length):
    __print_log__("single_capture")
    total_image_size = 0
    try:
        send_command(uart, command['single_capture'])
        recv_command(uart)
        # wait to recv camera data length
        time.sleep(wait_for_length)
        # recv image size
        response = recv_command(uart)
        if response[0] == HOST_CMD_CAM_CAMERA_DATA_LENGTH:
            total_image_size = (response[2]) | \
                               (response[3] << 8) | \
                               (response[4] << 16)
    except:
        __print_log__('single_capture: communication error!!')

    return total_image_size

def camera_data_ready(uart, timeout_s):
    # start time
    time_start = datetime.datetime.utcnow().timestamp()

    try:
        # command
        wait = True
        while wait:
            command = uart.read()
            command = int.from_bytes(command, 'little')
            if command == HOST_CMD_CAM_CAMERA_DATA_READY:
                wait = False
                __print_log__('image data is ready to dump')
            else:
                time_now = datetime.datetime.utcnow().timestamp()
                time_delta = time_now - time_start
                __print_log__('waiting for image data ready... %u/%u' % (time_delta, timeout_s))
                if time_delta > timeout_s:
                    __print_log__('waiting for image data ready timeout!!')
                    return False

        # payload length
        length = uart.read(1)
        length = int.from_bytes(length, 'little')

        # payload
        length -= 1 # remove end op code
        if length:
            uart.read(length)

        # end op code
        end_of_code = uart.read(1)
        end_of_code = int.from_bytes(end_of_code, 'little')
        if end_of_code != HOST_CMD_ENG_END_OP_CODE:
            __print_log__('wrong end of code: 0x%02x' % end_of_code)
            return False
    except:
        __print_log__('camera_data_ready: communication error!!')
        return False

    # done
    return True

def camera_data_upload(uart):
    try:
        send_command(uart, command['image_upload'])
        response = recv_command(uart)
        if response[0] == HOST_CMD_ACK and response[2] == HOST_CMD_RSP_ACK:
            __print_log__('camera_data_upload: ack')
            return True
    except:
        __print_log__('camera_data_upload: communication error!!')

    return False

def dump_camera_data(uart, image_size, timeout_s):
    # start time
    time_start = datetime.datetime.utcnow().timestamp()

    image_data = bytearray()
    recv_image_size = 0
    while recv_image_size < image_size:
        try:
            # command - must wait for the first command byte
            wait = True
            while wait:
                command = uart.read()
                command = int.from_bytes(command, 'little')
                if command == HOST_CMD_CAM_CAMERA_DATA:
                    wait = False
                else:
                    __print_log__('waiting for header... 0x%02x' % command)

            # payload length
            length = uart.read(1)
            length = int.from_bytes(length, 'little')

            # payload
            length -= 1 # remove end op code
            if length:
                image_data += uart.read(length)

            # end op code
            end_of_code = uart.read(1)
            end_of_code = int.from_bytes(end_of_code, 'little')
            if end_of_code != HOST_CMD_ENG_END_OP_CODE:
                __print_log__('wrong end of code: 0x%02x' % end_of_code)
                return None
        except:
            __print_log__('dump_camera_data: communication error!!')
            return None
        finally:
            recv_image_size += length

        time_now = datetime.datetime.utcnow().timestamp()
        time_delta = time_now - time_start
        if time_delta > timeout_s:
            __print_log__('dump_camera_data: time expire!!')
            return None

    __print_log__('dump_camera_data: recv= %lu' % recv_image_size)
    return image_data

def save_camera_image(camera_addr, camera_data):
    try:
        curr_time = datetime.datetime.now()
        file_name = ('camera_%s_%s.jpg' % (camera_addr, curr_time.strftime('%Y%m%d_%H.%M.%S')))
        f = open(file_name, 'wb')
        f.write(camera_data)
        f.close()
        __print_log__('output to %s' % file_name)
    except:
        __print_log__('save_camera_image: output jpg file error!!')

    return True

def dongle_reboot(uart):
    try:
        send_command(uart, command['dongle_reboot'])
    except:
        __print_log__('dongle_reboot: communication error!!')
        return

    __print_log__('dongle_reboot: ok')

def flush(uart):
    uart.flushInput()  # flush input buffer, discarding all its contents
    uart.flushOutput() # flush output buffer, aborting current output
                       # and discard all that is in buffer

def main():
    # open the port
    try:
        uart.open()
    except:
        __print_log__("error open serial port")
        exit()

    #uart.flushInput()  # flush input buffer, discarding all its contents
    #uart.flushOutput() # flush output buffer, aborting current output
                       # and discard all that is in buffer

    flush(uart)
    while True:
        # wait for BLE connection
        conn_counts = 0
        stats = BLE_STATS_IDLE
        addr = ''
        
        print('starting point------')

        ## s1: connecting to camera
        while stats != BLE_STATS_CONN:
            # get ble stats
            time.sleep(1)
            stats, addr = ble_stats(uart)
            if stats == BLE_STATS_IDLE:
                # start scanning
                ble_scan_onoff(uart, True)
            else:
                # in scanning
                conn_counts += 1
                if conn_counts >= ble_scan_period_time_second:
                    # something is wrong due to not connected out of capture period time
                    # reboot dongle
                    conn_counts = 0
                    dongle_reboot(uart)
                    time.sleep(5)

        # save camera device address
        if addr in device_camera:
            __print_log__('connected to camera index %u' % (device_camera.index(addr) + 1))
        else:
            device_camera.append(addr)
            __print_log__('connected to new camera at index %u' % (device_camera.index(addr) + 1))

        time.sleep(1)
        retry = 3
        ready, version, fmt, resolution = camera_stats(uart)

        ## s2: wait for camera ready
        while retry and not ready:
            time.sleep(1)
            ready, version, fmt, resolution = camera_stats(uart)
            retry -= 1

        # check camera stats
        if ready:
            # capture image
            time.sleep(0.1)
            image_size = single_capture(uart, 3)
            __print_log__('single captured: %lu bytes' % image_size)
            if image_size:
                # wait for data ready
                if camera_data_ready(uart, transmission_timeout_second):
                    # drop BLE connection
                    time.sleep(0.1)
                    ble_disconnect(uart, capture_period_time_second)
                    time.sleep(0.1)
                    time.sleep(1)

                    # wait for BLE disconnected
                    dis_counts = 0
                    reboot = False
                    while stats != BLE_STATS_IDLE:
                        time.sleep(1)
                        stats, not_used = ble_stats(uart)
                        # try to disconnect
                        dis_counts += 1
                        if dis_counts > 3:
                            ble_disconnect(uart, capture_period_time_second)
                            time.sleep(0.1)
                        # still can't drop ble connection
                        # reboot dongle to force ble disconnected
                        if dis_counts > 6:
                            __print_log__('reboot to force ble disconnected')
                            reboot = True
                            dongle_reboot(uart)
                            time.sleep(5)

                    if not reboot:
                        # request to upload camera data
                        camera_data_upload(uart)

                        # start to dump camera data
                        __print_log__('start image data uploading')
                        image_data = dump_camera_data(uart, image_size, transmission_timeout_second)
                        if image_data == None:
                            __print_log__('invalid camera data')
                        else:
                            save_camera_image(addr, image_data)
                            flush(uart)
                            __print_log__('completed')
                else:
                    __print_log__('image data is not available')
                    # self reboot
                    time.sleep(0.1)
                    dongle_reboot(uart)
                    # wait for BLE disconnect - dirty disconnected
                    __print_log__('waiting for BLE disconnected')
                    time.sleep(10)
                    __print_log__('done')
        else:
            __print_log__('camera is not ready to use!!')
            camera_reboot(uart)

        # wait for next session
        time.sleep(1)

    uart.close()

if __name__ == "__main__":
    main()
