from io import BytesIO
from time import sleep
from PIL import Image
from kafka import KafkaConsumer
from kafka import KafkaProducer
from datetime import datetime
import threading
import os
from os.path import dirname, abspath
import json
import logging

SAMPLING_TOPIC = 'device_sampling'
COMMANDS_TOPIC = 'model_commands_2'
CURRENT_DIR = os.path.split(os.path.realpath(__file__))[0]
PARENT_DIR = abspath(dirname(CURRENT_DIR))
DATA_DIR = PARENT_DIR + '/data'

LOG_PATH = CURRENT_DIR + '/log/'
LOG_FILE_PATH = LOG_PATH + 'main.log'

class PersistanceManager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        if not os.path.exists(LOG_PATH):
            os.makedirs(LOG_PATH)
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)
        logging.basicConfig(filename=LOG_FILE_PATH, format=log_format)
        # create logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.kafka_producer = KafkaProducer(bootstrap_servers=['10.249.77.87:9092'], api_version=(0,10))
        self.kafka_consumer = KafkaConsumer(SAMPLING_TOPIC, bootstrap_servers= ['10.249.77.87:9092'], api_version=(0,10))

    def _save_pic_file(self, device_id, filename, bin_stream):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        device_dir = DATA_DIR + '/' + device_id
        if not os.path.exists(device_dir):
            os.makedirs(device_dir)
        image = Image.open(BytesIO(bin_stream))
        file_path = device_dir + '/' + filename + '.jpg'
        image.save(file_path)
        return os.path.exists(file_path)

    def send_model_json(self, key, value):
        future = self.kafka_producer.send(COMMANDS_TOPIC, key=key, value=value, partition=0)
        future.get(timeout=10)

    def run(self):
        try:
            for msg in self.kafka_consumer:
                offset = msg.offset
                b_key = msg.key
                filename = b_key.decode('utf-8')
                device_id, _ = filename.split('_')
                b_picstream = msg.value
                if self._save_pic_file(device_id, filename, b_picstream):
                    # send model command to topic(model_commands)
                    b_device_id = bytes(device_id, 'ascii')
                    img_filename = filename + '.jpg'
                    model_msg = json.dumps({'device_id': device_id, 'file_name': img_filename})
                    b_msg = bytes(model_msg, 'ascii')
                    self.send_model_json(b_device_id, b_msg)
        finally:
            self.kafka_producer.close()

if __name__ == "__main__":
    pm = PersistanceManager()
    pm.start()            





    
    
