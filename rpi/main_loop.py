from imports import *
from camera import RaspberryCamera, SystemCamera, BleCameraController
from upload import HttpUploader, KafkaUploader
from conf import ConfigManager
import time
from datetime import datetime
import sys
import traceback


class StateController():
    def __init__(self, **kwargs):
        self._config = ConfigManager()
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(
            handler='TIME_FILE', 
            format=DEFAULT_LOG_FORMAT, 
            log_dir=LOG_PATH, 
            log_name=LOG_FILE_NAME)
        if LOG_REPORT_OPEN_STATUS == self._config.get_specific_attr('log_report'):
            loggerfactory.add_handler(
                handler='KAFKA', 
                is_json='True', 
                format=DEFAULT_LOG_FORMAT, 
                broker=self._config.get_kafka_brokers(), 
                topic=KAFKA_LOGS_TOPIC)
        self._logger = loggerfactory.get_logger()
        
        self._camera = self._select_camera()
        self._uploader = self._select_uploader()

    def execute(self):
        ## wait for camera initialization
        time.sleep(10)
        try:
            while True:
                try:
                    instruction = self._query_instruction()
                    start_ts = datetime.now()
                    self._switch_action(instruction)
                    end_ts = datetime.now()
                    residue = float(self._config.get_duration()) - (end_ts-start_ts).total_seconds()
                    if residue > 0:
                        time.sleep(residue)
                except SystemExit as e:
                    self._logger.error("SystemExit")
                    self.release()
                    self._config.join()
                    break
                except Exception as e:
                    self._logger.error(repr(e))
                    time.sleep(15)
        finally:
            pass

    def _query_instruction(self):
        return self._config.get_instruction()

    def _switch_action(self, instruction):
        name = '_action_' + instruction
        method = getattr(self, name, self._action_hang)
        return method()

    def _action_capture(self):
        ts_str, b_stream = self._camera.capture()
        device_id = self._config.get_device_id()
        file_name = device_id + '_' + ts_str + '.jpg'
        status, msg = self._uploader.send_pic_buf(device_id, file_name, b_stream)
        if not status:
            self._logger.error(msg)

    def _action_hang(self):
        # do nothing
        pass 

    def _action_quit(self):
        exit()

    def _select_camera(self):
        camera_type = self._config.get_specific_attr('camera_type')
        camera = None
        width = int(self._config.get_specific_attr('camera_width', 640))
        height = int(self._config.get_specific_attr('camera_height', 480))
        rotation = int(self._config.get_specific_attr('camera_rotation', 0))
        if GLB_RASPERRY_CAMERA == camera_type:
            camera = RaspberryCamera(width=width, height=height, rotation=rotation)
            self._config.register_device()
            self._config.start()
        elif GLB_SYSTEM_CAMERA == camera_type:
            camera = SystemCamera(width=width, height=height, rotation=rotation)
            self._config.register_device()
            self._config.start()
        elif GLB_BLUETOOTH_CAMERA == camera_type:
            camera = BleCameraController(self._config, width=width, height=height, rotation=rotation)
        return camera

    def _select_uploader(self):
        uploader_type = self._config.get_specific_attr('uploader_type')
        uploader = None
        if GLB_HTTP_UPLOADER == uploader_type:
            uploader = HttpUploader(
                self._config.get_specific_attr('app_server'),
                self._config.get_specific_attr('app_port')
            )
        elif GLB_KAFKA_UPLOADER == uploader_type:
            uploader = KafkaUploader(
                self._config.get_kafka_brokers(),
                KAFKA_LOGS_TOPIC
            )
        return uploader

    def release(self):
        self._uploader.close()
        self._config.release()


if __name__ == "__main__":
    main_loop_controller = StateController()
    main_loop_controller.execute()