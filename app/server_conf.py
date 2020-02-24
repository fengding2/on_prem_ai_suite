from app_global_imports import *
from zk_utils import *
import configparser
import logging
import json
import time
import hashlib
import os
import threading
from datetime import datetime
from kazoo.client import KazooClient

class ServerConf(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self.logger = loggerfactory.get_logger()
        self._init_zk_client()
        self._devices_info = {}
        self._devices_md5 = None

    def _init_zk_client(self):
        zk_servers = os.getenv('ZOOKEEPER', '10.249.77.186:2181')
        self.zk_client = KazooClient(hosts=zk_servers, timeout=10.0, logger=logging)
        self.zk_client.start()
    
    def get_kafka_brokers(self):
        broker_ips = []
        if self.zk_client.exists(ZK_BROKERS_NODE) != None:
            for id in self.zk_client.get_children(ZK_BROKERS_NODE):
                da, _ = self.zk_client.get(ZK_BROKERS_NODE + '/' + id)
                cont = json.loads(da.decode('ascii'))
                ip = cont['host'] + ':' + str(cont['port'])
                broker_ips.append(ip)
        return broker_ips

    def _refresh_device_info(self):
        latest_info = get_all_devices_info(self.zk_client, ZK_DEVICES_NODE)
        sorted_info = json.dumps(latest_info, sort_keys=True)
        last_md5 = hashlib.md5(sorted_info.encode('ascii')).hexdigest()
        if last_md5 != self._devices_md5:
            self._devices_info = latest_info
            self._devices_md5 = last_md5

    def get_zk_client(self):
        ## supply zookeeper client for device querying directly
        return self.zk_client

    def get_devices_info(self):
        return self._devices_info
    
    def get_device_fields(self, device_id):
        info = self._devices_info.get(device_id)
        if info is None:
            return {}
        return info
    
    def run(self):
        while True:
            try:
                ## query device periodically
                ## refresh the info cache if changed
                self._refresh_device_info()
            except Exception as e:
                self.logger.error(repr(e))
            time.sleep(60)
        self.release()

    def release(self):
        self.zk_client.close()


if __name__ == "__main__":
    conf = ServerConf()
    conf.start()