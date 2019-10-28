from app_global_imports import *
from zk_utils import *

class ZookeeperService():
    def __init__(self, configurer):
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self._logger = loggerfactory.get_logger()
        self._zk_client = configurer.get_zk_client()

    def get_devices_info(self, query_id=None):
        info = []
        if not self._zk_client.exists(ZK_DEVICES_NODE):
            raise ZookeeperServiceException("node doesn't exist")
        device_ids = self._zk_client.get_children(ZK_DEVICES_NODE)
        if query_id:
            if query_id in device_ids:
               device_path = ZK_DEVICES_NODE + '/' + query_id
               info.append(get_device_fields(self._zk_client, device_path))
        else:
            for device_id in device_ids:
                device_path = ZK_DEVICES_NODE + '/' + device_id
                info.append(get_device_fields(self._zk_client, device_path))
        return info

    def set_device_info(self, device_id, **kwargs):
        duration = kwargs.pop(ZK_DEVICE_DURATION_KEY, None)
        instruction = kwargs.pop(ZK_DEVICE_INSTRUCTION_KEY, None)
        if not self._does_device_exist(device_id):
            return (False, 'device cannot be found')
        if duration:
            status, msg = self._set_device_field(device_id, ZK_DEVICE_DURATION_KEY, duration)
            if not status:
                return (False, msg)
        if instruction:
            status, msg = self._set_device_field(device_id, ZK_DEVICE_INSTRUCTION_KEY, instruction)
            if not status:
                return (False, msg)
        return (True, "Done")
    
    def _does_device_exist(self, device_id):
        device_path = ZK_DEVICES_NODE + '/' + device_id
        if not self._zk_client.exists(device_path): 
            return False
        else:
            return True

    def _set_device_field(self, device_id, key, value):
        field_path = ZK_DEVICES_NODE + '/' + device_id + '/' + key
        if True != self._zk_client.ensure_path(field_path):
            if True == self._zk_client.ensure_path(field_path):
                self._zk_client.set(field_path, bytes(value, 'ascii'))
                return (True, 'Done')
            else:
                msg = "creating zk field path %s fails" % field_path
                self._logger.error(msg)
                return (False, msg)
        else: 
            self._zk_client.set(field_path, bytes(value, 'ascii'))
            return (True, 'Done')
