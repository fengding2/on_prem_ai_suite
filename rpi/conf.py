from imports import *
import configparser
import threading
import netifaces
import logging
import json
import time
import os
from datetime import datetime
from kazoo.client import KazooClient
from kazoo.recipe.watchers import DataWatch


class ConfigManager(threading.Thread):
    def __init__(self):
        self._stop_thread = False
        self._registered_state = False
        threading.Thread.__init__(self)
        ## init logger
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self.logger = loggerfactory.get_logger()
        self.conf = configparser.ConfigParser()
        if len(self.conf.read(GLB_CONF_FILE)) == 0:
            self.logger.error("reading config file %s fails" % GLB_CONF_FILE)
            raise RuntimeError("reading config file %s fails" % GLB_CONF_FILE)
        ## read conf from local conf_file
        self._load_local_conf()
        self.ip_address = self._get_ip_address()
        #self.mac_address = ConfigManager._get_mac_address()
        self.duration = ZK_DEFAULT_DURATION
        self.instruction = ZK_DEFAULT_INSTRUCTION
        self.heartbeat = None
        if os.getenv('CAPTURE_INTERVAL') is None:
            self.heartbeat_interval = DEFAULT_INTERVAL
        else:
            self.heartbeat_interval = os.getenv('CAPTURE_INTERVAL')
        self._init_zk_client()
        self.register_device()

    def get_description(self):
        return self.description

    def get_device_id(self):
        return self.mac_address

    def get_ip_address(self):
        return self.ip_address

    def get_zk_servers(self):
        return self.zk_servers

    def get_duration(self):
        return self.duration

    def get_instruction(self):
        return self.instruction

    def set_heartbeat(self, device_id, heartbeat):
        self.heartbeat = heartbeat

    def get_kafka_brokers(self):
        broker_ips = []
        if self.zk_client.exists(ZK_BROKERS_NODE) != None:
            for id in self.zk_client.get_children(ZK_BROKERS_NODE):
                da, _ = self.zk_client.get(ZK_BROKERS_NODE + '/' + id)
                cont = json.loads(da.decode('ascii'))
                ip = cont['host'] + ':' + str(cont['port'])
                broker_ips.append(ip)
        return broker_ips

    def _load_local_conf(self):
        self.zk_servers = json.loads(self.conf['zookeeper']['servers'])
        self.description = self.conf['device']['description']
        self.device_type = self.conf['device']['camera_type']
        self.network_interface = self.conf['device']['network_interface']
        if os.getenv('CAMERA_ROTATION') is None:
            self.camera_rotation = int(self.conf['device']['camera_rotation'])
        else:
            self.camera_rotation = int(os.getenv('CAMERA_ROTATION')) 
        self.camera_width = int(self.conf['device']['camera_width'])
        self.camera_height = int(self.conf['device']['camera_height'])
        self.camera_type = self.conf['device']['camera_type']
        self.uploader_type = self.conf['device']['uploader_type']
        self.log_report = self.conf['device']['log_report']
        self.app_url = self.conf['app']['app_url']
        self.app_server = self.conf['app']['app_server']
        self.app_port = self.conf['app']['app_port']
        self.img_topic = self.conf['app']['img_topic']
        self.log_topic = self.conf['app']['log_topic']
        self.heartbeat_url = self.conf['app']['heartbeat_url']

    def get_heartbeat_interval(self):
        return self.heartbeat_interval

    def get_specific_attr(self, attr_name, default=None):
        if default is None:
            default = 'unknown'
        return getattr(self, attr_name, default)

    def _init_zk_client(self):
        zk_ips = ','.join(self.zk_servers)
        self.zk_client = KazooClient(hosts=zk_ips, timeout=10.0, logger=logging)
        self.zk_client.start()

    def send_heartbeat(self, device_id, timestamp):
        pass

    def register_device(self, device_addr=None, active_heartbeat=True):
        self.active_heartbeat = active_heartbeat
        self.mac_address = ConfigManager._get_mac_address() if not device_addr else device_addr
        self.zk_client.ensure_path(self._get_zk_device_path())
        if self.zk_client.ensure_path(self._get_zk_device_path()):
            ts = ConfigManager._get_timestamp_now()
            self._set_zk_device_info(ZK_DEVICE_IP_KEY, self.ip_address)
            self._set_zk_device_info(ZK_DEVICE_TYPE_KEY, self.device_type)
            self._set_zk_device_info(ZK_DEVICE_MAC_KEY, self.mac_address)
            self._set_zk_device_info(ZK_DEVICE_DESC_KEY, self.description)
            self._set_zk_device_info(ZK_DEVICE_DURATION_KEY, self.duration)
            self._add_zk_watcher(ZK_DEVICE_DURATION_KEY, self._duration_changed_handler)
            self._set_zk_device_info(ZK_DEVICE_INSTRUCTION_KEY, ZK_DEFAULT_INSTRUCTION)
            self._add_zk_watcher(ZK_DEVICE_INSTRUCTION_KEY, self._instruction_changed_handler)
            self._set_zk_device_info(ZK_DEVICE_INIT_TS_KEY, ts)
            self._set_zk_device_info(ZK_DEVICE_LAST_TS_KEY, ts)
            self._registered_state = True
        else:
            self.logger.error("creating zk device node fails")
        return self._registered_state

    def _add_zk_watcher(self, key, handler):
        zk_node = self._get_zk_device_info_path(key)
        DataWatch(self.zk_client, zk_node, handler)

    def _duration_changed_handler(self, data, stat):
        if stat is not None:
            self.duration = data.decode('ascii')

    def _instruction_changed_handler(self, data, stat):
        if stat is not None:
            self.instruction = data.decode('ascii')

    def _set_zk_device_info(self, key, value):
        zk_node = self._get_zk_device_info_path(key)
        if True != self.zk_client.ensure_path(zk_node):
            if True == self.zk_client.ensure_path(zk_node):
                self.zk_client.set(zk_node, bytes(value, 'ascii'))
            else:
                self.logger.error("creating zk device info %s fails" % zk_node)

    def _get_zk_device_path(self):
        return ZK_ROOT_NODE + self.mac_address

    def _get_zk_device_info_path(self, key):
        return self._get_zk_device_path() + '/' + key

    @staticmethod
    def _get_timestamp_now():
        return str(int(datetime.timestamp(datetime.now())))

    def _get_ip_address(self):
        ip = netifaces.ifaddresses(self.network_interface)[netifaces.AF_INET][0]['addr']
        return ip

    @staticmethod
    def _get_mac_address():
        import uuid
        node = uuid.getnode()
        mac = uuid.UUID(int = node).hex[-12:]
        return mac

    def run(self):
        while True:
            time.sleep(15)
            try:
                system_heartbeat = ConfigManager._get_timestamp_now()
                current_heartbeat = system_heartbeat if self.active_heartbeat else self.heartbeat
                if self._registered_state:
                    self._set_zk_device_info(ZK_DEVICE_LAST_TS_KEY, current_heartbeat)
                if self._stop_thread:
                    break
            except Exception as e:
                self.logger.error(repr(e))

        self.release()

    def release(self):
        try:
            self.zk_client.stop()
            self._stop_thread = True
        except Exception:
            self.logger.error(traceback.format_exc())



if __name__ == "__main__":
    config_manager = ConfigManager()
    config_manager.start()