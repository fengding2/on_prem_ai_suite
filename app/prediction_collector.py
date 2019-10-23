from app_global_imports import *
from kafka import KafkaConsumer
import threading
import json
from json import JSONDecodeError
import logging
from datetime import datetime
from area_slicer import AreaSlicer
import time 
import uuid


## utility for constructing dashboard data
def dashboard_data(device_id, desc, file_name, boxes):
    data = {}
    data["actor"] = {"type": "Camera", "displayName": "Raspberry Pi", "id": device_id, "mac": device_id}
    data["verb"] = "recognize"
    data["location"] =  {"id": "b12-asdf-afa", "type": "Floor"}   
    data["publish"] = datetime.now().strftime("%Y-%M-%d, %H:%M:%S")
    data["ec_event_time"] = int(time.time() * 1000)
    data["ec_event_id"] = str(uuid.uuid1())
    data["result"] = {}
    positions = []
    behaviors = []
    areas = []
    for box in boxes:
        behavior = ','.join(box['activities'])
        position = {"x": box['loc'][0], "y": box['loc'][1], "w": box['loc'][2], "h": box['loc'][3]}
        area = AreaSlicer.get_area(device_id, position["x"], position["y"], position["w"], position["h"])
        positions.append(position)
        behaviors.append(behavior)
        areas.append(area)
    data["result"]["positions"] = positions
    data["result"]["behaviors"] = behaviors
    data["result"]["areas"] = areas
    data["result"]["source"] = file_name
    data["result"]["count"] = len(data["result"]["positions"])
    data["result"]["type"] = "Person"
    return data


class CollectManager(threading.Thread):
    def __init__(self, brokers, topic, publisher=None, configurer=None):
        threading.Thread.__init__(self)
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self.logger = loggerfactory.get_logger()
        self.kafka_consumer = KafkaConsumer(topic, bootstrap_servers=brokers, api_version=(0,10))
        self.file_handlers = {}
        self.publisher = publisher
        self.configurer = configurer
        AreaSlicer.pre_load()

    def save_backup_log(self, device_id, date, raw_value):
        file_name = device_id + '_' + date + '.txt'
        file_path = OUTPUT_DIR + '/' + file_name
        fh = None
        if None == self.file_handlers.get(device_id):
            fh = open(file_path, 'a+')
            self.file_handlers[device_id] = fh
        else:
            fh = self.file_handlers[device_id]
            if fh.name != file_name:
                fh.close()
                fh = open(file_path, 'a+')
                self.file_handlers[device_id] = fh
        fh.write(raw_value + '\n')

    def _get_device_description(self, device_id):
        if self.configurer is None:
            return GLB_DEFAULT_STR
        info = self.configurer.get_device_fields(device_id)
        if info is None or info['description'] is None:
            return GLB_DEFAULT_STR
        return info['description'] 

    def publish_dashboard(self, device_id, file_name, boxes):
        if self.publisher is not None:
            desc = self._get_device_description(device_id)
            data_to_send = dashboard_data(device_id, desc, file_name, boxes)
            self.publisher.send_data(data_to_send)

    def run(self):
        for msg in self.kafka_consumer:
            try:
                raw_value = msg.value.decode('utf-8')
                result_json = json.loads(raw_value)
                device_id = result_json['device_id']
                file_name = result_json['file_name']
                boxes = result_json['boxes']
                ts = file_name.split('.')[0].split('_')[1]
                date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                self.save_backup_log(device_id, date, raw_value)
                self.publish_dashboard(device_id, file_name, boxes)
            except Exception as e:
                self.logger.error(e)
            