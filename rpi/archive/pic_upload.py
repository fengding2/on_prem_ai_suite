from picamera import PiCamera
from camera import RaspberryCamera, SystemCamera
from datetime import datetime
from conf import ConfigManager
from kafka import KafkaProducer
import io
import os
import time
import logging


class Camera():
    def __init__(self, rotation=180, resolution=(640, 480)):
        self._camera = PiCamera()
        self._camera.resolution = resolution
        self._camera.rotation = rotation

    def capture(self):
        now = datetime.now()
        buf = io.BytesIO()
        self._camera.capture(buf, 'jpeg')
        return str(int(now.timestamp())), buf.getbuffer()

class KafkaClient():
    def __init__(self, brokers, topic):
        self._producer = KafkaProducer(bootstrap_servers=brokers, api_version=(0,10))
        self._topic = topic
    
    def send_pic_buf(self, key, value):
        try:
            future = self._producer.send(self._topic, key=key, value=value, partition=0)
            future.get(timeout=10)
        except Exception:
            logging.error("")

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
                b_msg_key = bytes(self._device_id + '_' + ts_str, 'ascii')
                self._kafka.send_pic_buf(b_msg_key, b_msg_val)
                end_ts = datetime.now()
                residue = float(self._config.get_duration()) - (end_ts-start_ts).total_seconds()
                if residue > 0:
                    time.sleep(residue)
        finally:
            self.destroy()
            
    def destroy(self):
        self._config.destroy()
        self._kafka.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, filename="log/camera.log", format="%(asctime)s;%(levelname)s;%(message)s")
    proc = SamplingProc(topic=TOPIC)
    proc.execute()
