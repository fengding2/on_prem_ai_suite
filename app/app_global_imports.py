import sys
import os
import traceback
from os.path import dirname, abspath
from exceptions import *

## add the root path into path env
dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(dir_path)

## constant about log
from logger_utils import JsonFormatter, LoggerFactory
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(module)s - %(levelname)s - %(message)s'
CURRENT_DIR = os.path.split(os.path.realpath(__file__))[0]
PARENT_DIR = abspath(dirname(CURRENT_DIR))
LOG_PATH = CURRENT_DIR + '/logs/'
LOG_FILE_NAME = 'server.log'

DATA_DIR = PARENT_DIR + '/data'
OUTPUT_DIR = PARENT_DIR + '/out'

## configuration file path
GLB_CONF_FILE = CURRENT_DIR + '/server_conf.ini'
GLB_INVALID = ['INVALID', 'unknown']
GLB_DEFAULT_STR = 'unknown'

## constant about kafka
KAFKA_LOGS_TOPIC = 'device_logs'
KAFKA_SAMPLING_TOPIC = 'device_sampling'
KAFKA_COMMANDS_TOPIC = 'model_commands'
KAFKA_PREDICTION_TOPIC = 'model_results'

##------- zookeeper metadata below-------
ZK_DEVICES_NODE = '/devices'
ZK_BROKERS_NODE = '/brokers/ids'

ZK_DEVICE_IP_KEY = 'ip_address'
ZK_DEVICE_MAC_KEY = 'mac_address'
ZK_DEVICE_DESC_KEY = 'description'
ZK_DEVICE_INIT_TS_KEY = 'initial_ts'
ZK_DEVICE_LAST_TS_KEY = 'last_ts'
ZK_DEVICE_DURATION_KEY = 'duration'
ZK_DEVICE_TYPE_KEY = 'type'
ZK_DEVICE_INSTRUCTION_KEY = 'instruction'
##------- zookeeper metadata above -------

DASHBOARD_URL = "https://eventcollector.enigma.wwrkr.cn"
DASHBOARD_APPNAME = "appliedscience"
DASHBOARD_PSWORD = "NzE0ODFBYzkwRDc5Q0VhQWM5MTVkN0Q5MTllQzMz"
DASHBOARD_EVENTNAME = "engagement-event"
DASHBOARD_SCHEMA_PATH = CURRENT_DIR + "/activity_chn.avro"

##------- global utility functions ---------
def is_param_invalid(param):
    return param in GLB_INVALID

def is_empty_list(param):
    return len(param) == 0

##------- initial device log directory -------
if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
