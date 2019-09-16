from kafka import KafkaConsumer
import threading
import os
from os.path import dirname, abspath
import cv2
import json
from json import JSONDecodeError
import logging

RESULTS_TOPIC = 'model_results'
CURRENT_DIR = os.path.split(os.path.realpath(__file__))[0]
PARENT_DIR = abspath(dirname(CURRENT_DIR))
DATA_DIR = PARENT_DIR + '/data'
RESULT_DIR = PARENT_DIR + '/out'

LOG_PATH = CURRENT_DIR + '/log/'
LOG_FILE_PATH = LOG_PATH + 'main.log'

class CollectManager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)
        logging.basicConfig(filename=LOG_FILE_PATH, format=log_format)
        # create logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.kafka_consumer = KafkaConsumer(RESULTS_TOPIC, bootstrap_servers= ['10.249.77.87:9092'], api_version=(0,10))

    def draw_rectangle(self, device_id, file_name, boxes):
        file_path = DATA_DIR + '/' + device_id + '/' + file_name
        img = cv2.imread(file_path, cv2.IMREAD_COLOR)
        for box in boxes:
            text = box['activities']
            [x, y, w, h] = box['loc']
            # Get the unique color for this class
            color = [0,255,0]
            # Draw the bounding box rectangle and label on the image
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
            if len(text) > 0:
                cv2.putText(img, text[0], (x+5, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return img

    def save_result_img(self, device_id, file_name, img):
        if not os.path.exists(RESULT_DIR):
            os.makedirs(RESULT_DIR)
        device_dir = RESULT_DIR + '/' + device_id
        if not os.path.exists(device_dir):
            os.makedirs(device_dir)
        output_path = device_dir + '/' + file_name
        cv2.imwrite(output_path,img)
    
    def run(self):
        try:
            for msg in self.kafka_consumer:
                try:
                    raw_value = msg.value.decode('utf-8')
                    result_json = json.loads(raw_value)
                    device_id = result_json['device_id']
                    file_name = result_json['file_name']
                    boxes = result_json['boxes']
                    img = self.draw_rectangle(device_id, file_name, boxes)
                    self.save_result_img(device_id, file_name, img)
                except Exception as e:
                    self.logger.error(e)
        finally:
            pass

    