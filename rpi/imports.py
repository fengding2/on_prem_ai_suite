import sys
import os
import traceback
## add the root path into path env
dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(dir_path)

## constant about log
from logger_utils import JsonFormatter, LoggerFactory
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
CURRENT_DIR = os.path.split(os.path.realpath(__file__))[0]
LOG_PATH = CURRENT_DIR + '/logs/'
LOG_FILE_NAME = 'rpi.log'

## configuration file path
GLB_CONF_FILE = CURRENT_DIR + '/device_conf.ini'
GLB_SYSTEM_CAMERA = 'SystemCamera'
GLB_RASPERRY_CAMERA = 'RaspberryCamera'
GLB_BLUETOOTH_CAMERA = 'BleCameraController'
GLB_HTTP_UPLOADER = 'HttpUploader'
GLB_KAFKA_UPLOADER = 'KafkaUploader'
GLB_INVALID = ['INVALID', 'unkown']

LOG_REPORT_OPEN_STATUS = 'open'

## constant about kafka
KAFKA_UPLOAD_TOPIC = "device_sampling"
KAFKA_LOGS_TOPIC = 'device_logs'

##------- zookeeper metadata below-------
ZK_ROOT_NODE = '/devices/'
ZK_BROKERS_NODE = '/brokers/ids'

ZK_DEVICE_IP_KEY = 'ip_address'
ZK_DEVICE_MAC_KEY = 'mac_address'
ZK_DEVICE_DESC_KEY = 'description'
ZK_DEVICE_INIT_TS_KEY = 'initial_ts'
ZK_DEVICE_LAST_TS_KEY = 'last_ts'
ZK_DEVICE_DURATION_KEY = 'duration'
ZK_DEVICE_TYPE_KEY = 'type'
ZK_DEVICE_INSTRUCTION_KEY = 'instruction'

ZK_DEFAULT_DURATION = '60'
ZK_DEFAULT_INSTRUCTION = 'capture'
DEFAULT_INTERVAL = '60'
##------- zookeeper metadata above -------


##------- global utility functions ---------
def is_param_invalid(param):
    return param in GLB_INVALID

def is_empty_list(param):
    return len(param) == 0

##------- initial device log directory -------
if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)