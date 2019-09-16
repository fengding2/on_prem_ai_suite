import configparser
import threading
import netifaces
import logging
import logging.config
import json
import time
import os
from datetime import datetime
from kazoo.client import KazooClient
from kazoo.recipe.watchers import DataWatch

CURRENT_DIR = os.path.split(os.path.realpath(__file__))[0]
CONF_FILE = CURRENT_DIR + '/device_conf.ini'
LOG_PATH = CURRENT_DIR + '/log/'
LOG_FILE_PATH = LOG_PATH + 'camera.log'
ZK_ROOT_NODE = '/devices/'
ZK_BROKERS_NODE = '/brokers/ids'

ZK_DEVICE_IP_KEY = 'ip_address'
ZK_DEVICE_MAC_KEY = 'mac_address'
ZK_DEVICE_DESC_KEY = 'description'
ZK_DEVICE_INIT_TS_KEY = 'initial_ts'
ZK_DEVICE_LAST_TS_KEY = 'last_ts'
ZK_DEVICE_DURATION_KEY = 'duration'

DEFAULT_DURATION = '5'

class ConfigManager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._init_logger()
        self.conf = configparser.ConfigParser()
        if len(self.conf.read(CONF_FILE)) == 0:
            self.logger.error("reading config file %s fails", CONF_FILE)
            raise RuntimeError("reading config file %s fails" % CONF_FILE)
        self._load_local_conf()
        self.ip_address = self._get_ip_address()
        self.mac_address = ConfigManager._get_mac_address()
        self.duration = DEFAULT_DURATION
        self._register_device()

    def get_description(self):
        return self.description

    def get_device_id(self):
        return self.mac_address

    def get_zk_servers(self):
        return self.zk_servers

    def get_duration(self):
        return self.duration

    def get_camera_rotation(self):
        return self.camera_rotation

    def get_kafka_brokers(self):
        broker_ips = []
        if self.zk_client.exists(ZK_BROKERS_NODE) != None:
            for id in self.zk_client.get_children(ZK_BROKERS_NODE):
                da, _ = self.zk_client.get(ZK_BROKERS_NODE + '/' + id)
                cont = json.loads(da.decode('ascii'))
                ip = cont['host'] + ':' + str(cont['port'])
                broker_ips.append(ip)
        return broker_ips

    def _init_logger(self):
        if not os.path.exists(LOG_PATH):
            os.makedirs(LOG_PATH)
        # create formatter
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)
        logging.basicConfig(filename=LOG_FILE_PATH, format=log_format)
        # create logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to logger
        self.logger.addHandler(ch)

    def _load_local_conf(self):
        self.zk_servers = json.loads(self.conf['zookeeper']['servers'])
        self.description = self.conf['device']['description']
        self.network_interface = self.conf['device']['network_interface']
        self.camera_rotation = int(self.conf['device']['camera_rotation'])

    def _register_device(self):
        zk_ips = ','.join(self.zk_servers)
        self.zk_client = KazooClient(hosts=zk_ips, timeout=10.0, logger=logging)
        self.zk_client.start()
        self.zk_client.ensure_path(self._get_zk_device_path())
        if self.zk_client.ensure_path(self._get_zk_device_path()):
            ts = ConfigManager._get_timestamp_now()
            self._set_zk_device_info(ZK_DEVICE_IP_KEY, self.ip_address)
            self._set_zk_device_info(ZK_DEVICE_MAC_KEY, self.mac_address)
            self._set_zk_device_info(ZK_DEVICE_DESC_KEY, self.description)
            self._set_zk_device_info(ZK_DEVICE_DURATION_KEY, self.duration)
            self._add_duration_watcher(ZK_DEVICE_DURATION_KEY)
            self._set_zk_device_info(ZK_DEVICE_INIT_TS_KEY, ts)
            self._set_zk_device_info(ZK_DEVICE_LAST_TS_KEY, ts)
        else:
            self.logger.error("creating zk device node fails")

    def _add_duration_watcher(self, key):
        zk_node = self._get_zk_device_info_path(key)
        DataWatch(self.zk_client, zk_node, self._duration_changed)

    def _duration_changed(self, data, stat):
        if stat is not None:
            self.duration = data.decode('ascii')

    def _set_zk_device_info(self, key, value):
        zk_node = self._get_zk_device_info_path(key)
        if self.zk_client.ensure_path(zk_node):
            if self.zk_client.ensure_path(zk_node):
                self.zk_client.set(zk_node, bytes(value, 'ascii'))
            else:
                self.logger.error("creating zk device info %s fails", zk_node)

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
        try:
            while True:
                ts = ConfigManager._get_timestamp_now()
                self._set_zk_device_info(ZK_DEVICE_LAST_TS_KEY, ts)
                self.logger.info("send heartbeat when timestamp is %s", ts)
                # print("fps is %s" % self.fps)
                time.sleep(10)
        finally:
            self.destroy()

    def destroy(self):
        self.zk_client.stop()


if __name__ == "__main__":
    config_manager = ConfigManager()
    config_manager.start()