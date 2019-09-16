from kafka import KafkaConsumer
import threading
import os
from os.path import dirname, abspath
import cv2
import json
from json import JSONDecodeError

RESULTS_TOPIC = 'model_results'
CURRENT_DIR = os.path.split(os.path.realpath(__file__))[0]
PARENT_DIR = abspath(dirname(CURRENT_DIR))
DATA_DIR = PARENT_DIR + '/data'
RESULT_DIR = PARENT_DIR + '/out'

class CollectManager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.logger = None
        self.kafka_consumer = KafkaConsumer(RESULTS_TOPIC, bootstrap_servers= ['10.249.77.87:9092'], api_version=(0,10))

    def draw_rectangle(self, device_id, file_name, boxes):
        file_path = DATA_DIR + '/' + device_id + '/' + file_name
        img = cv2.imread(file_path, cv2.IMREAD_COLOR)
        for box in boxes:
            activity_label = box['activities'][0]
            [x, y, w, h] = box['loc']
            text = activity_label
            # Get the unique color for this class
            color = [0,255,0]
            # Draw the bounding box rectangle and label on the image
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
            cv2.putText(img, text, (x+5, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
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
                raw_value = msg.value.decode('utf-8')
                result_json = json.loads(raw_value)
                device_id = result_json['device_id']
                file_name = result_json['file_name']
                boxes = result_json['boxes']
                img = self.draw_rectangle(device_id, file_name, boxes)
                self.save_result_img(device_id, file_name, img)
        except JSONDecodeError:
            pass
        finally:
            pass

    