import cv2
from datetime import datetime
from conf import ConfigManager
from kafka import KafkaProducer
import io
import os
import time
import logging
from PIL import Image

TOPIC = "device_sampling"

class Camera():
    def __init__(self, rotation=180, resolution=(640, 480)):
        self._camera = cv2.VideoCapture(0)
        self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def capture(self):
        now = datetime.now()
        buf = io.BytesIO()
        ret, frame = self._camera.read()
        img_crop_pil = Image.fromarray(frame)
        img_crop_pil.save(buf, format="JPEG")
        return str(int(now.timestamp())), buf.getbuffer()

class KafkaClient():
    def __init__(self, brokers, topic):
        self._producer = KafkaProducer(bootstrap_servers=brokers, api_version=(0,10))
        self._topic = topic
    
    def send_pic_buf(self, key, value):
        future = self._producer.send(self._topic, key=key, value=value, partition=0)
        future.get(timeout=10)

    def close(self):
        self._producer.close()

class SamplingProc():
    def __init__(self, topic):
        self._config = ConfigManager()
        self._device_id = self._config.get_device_id()
        self._config.start()
        self._camera = Camera(self._config.get_camera_rotation())
        kafka_brokers = self._config.get_kafka_brokers()
        self._kafka = KafkaClient(kafka_brokers, topic)

    def execute(self):
        try:
            while True:
                start_ts = datetime.now()
                ts_str, b_msg_val = self._camera.capture()
                capture_ts = datetime.now()
                b_msg_key = bytes(self._device_id + '_' + ts_str, 'ascii')
                self._kafka.send_pic_buf(b_msg_key, b_msg_val)
                end_ts = datetime.now()
                whole_dura = (end_ts-start_ts).total_seconds()
                capture_dura = (capture_ts-start_ts).total_seconds()
                print('total time consumption %f, capture ts %f' % (whole_dura, capture_dura))
                residue = float(self._config.get_duration()) - (end_ts-start_ts).total_seconds()
                if residue > 0:
                    time.sleep(residue)
        except Exception as e:
            print(e)
        finally:
            self.destroy()
            
    def destroy(self):
        self._config.join()
        self._kafka.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, filename="log/camera.log", format="%(asctime)s;%(levelname)s;%(message)s")
    proc = SamplingProc(topic=TOPIC)
    proc.execute()
