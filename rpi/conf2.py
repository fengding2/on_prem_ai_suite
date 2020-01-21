from imports import *
import configparser
import psutil
import requests
import json

class ConfigManagerV2():
    def __init__(self):
        self._registered_state = False
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
        self.device_id = ConfigManagerV2._get_mac_address()
        self.heartbeat_interval = DEFAULT_INTERVAL

    def _load_local_conf(self):
        self.description = self.conf['device']['description']
        self.device_type = self.conf['device']['device_type']
        self.device_role = self.conf['device']['device_role']
        self.camera_rotation = int(self.conf['device']['camera_rotation'])
        self.camera_width = int(self.conf['device']['camera_width'])
        self.camera_height = int(self.conf['device']['camera_height'])
        self.camera_type = self.conf['device']['camera_type']
        self.uploader_type = self.conf['device']['uploader_type']
        self.app_url = self.conf['app']['app_url']
        self.heartbeat_url = self.conf['app']['heartbeat_url']

    def get_heartbeat_interval(self):
        return self.heartbeat_interval

    def get_device_id(self):
        return self.device_id

    def get_specific_attr(self, attr_name, default=None):
        if default is None:
            default = 'unkown'
        return getattr(self, attr_name, default)

    def send_heartbeat(self, device_id, timestamp):
        request_url = self.heartbeat_url + '/heartbeat?device_name=' + device_id
        snapshot = self.get_system_snapshot()
        snapshot['heartbeat'] = int(timestamp)
        s = json.dumps(snapshot)
        s = s.encode('utf-8')
        print(s)
        try:
            r = requests.post(request_url, s)
            if 200 != r.status_code:
                return False, "heartbeat wrong status"
            else:
                return True, "success"
        except Exception as e:
            print(traceback.format_exc(e))
            return False, "heartbeat request exception"

    def get_system_snapshot(self):
        snapshot =  {}
        snapshot['device_type'] = self.device_type
        snapshot['device_role'] = self.device_role
        snapshot['cpu'] = psutil.cpu_percent() / 100
        snapshot['mem'] = psutil.virtual_memory().percent / 100
        snapshot['cpu_cores'] =  4
        snapshot['mem_cap'] = 1024
        return snapshot

    def get_app_url(self):
        return self.app_url

    @staticmethod
    def _get_mac_address():
        import uuid
        node = uuid.getnode()
        mac = uuid.UUID(int = node).hex[-12:]
        return mac