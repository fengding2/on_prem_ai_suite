from imports import *
from camera import RaspberryCamera, SystemCamera, BleCameraController
from upload import HttpUploader, KafkaUploader
from conf2 import ConfigManagerV2
import time
from datetime import datetime
import sys
import traceback

def timestamp_string():
    return str(int(time.time()))

def json_log_build(conf, msg):
    content = {}
    content['device_id'] = conf.get_device_id()
    content['timestamp'] = timestamp_string()
    content['msg'] = msg
    return content

class StateController():
    def __init__(self, **kwargs):
        self._config = ConfigManagerV2()
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(
            handler='TIME_FILE', 
            format=DEFAULT_LOG_FORMAT, 
            log_dir=LOG_PATH, 
            log_name=LOG_FILE_NAME)
        self._logger = loggerfactory.get_logger()
        
        self._camera = self._select_camera()
        self._uploader = self._select_uploader()

    def execute(self):
        ## wait for camera initialization
        time.sleep(10)
        try:
            while True:
                try:
                    start_ts = datetime.now()
                    self._action_capture()
                    end_ts = datetime.now()
                    residue = float(self._config.get_heartbeat_interval()) - (end_ts-start_ts).total_seconds()
                    if residue > 0:
                        time.sleep(residue)
                except SystemExit as e:
                    info = json_log_build(self._config, "SystemExit")
                    self._logger.error(info)
                    self.release()
                    break
                except Exception as e:
                    info = json_log_build(self._config, repr(e))
                    self._logger.error(info)
                    time.sleep(15)
        finally:
            pass

    def _switch_action(self, instruction):
        name = '_action_' + instruction
        method = getattr(self, name, self._action_hang)
        return method()

    def _action_capture(self):
        contents = self._camera.capture()
        for content in contents:
            device_id = content['device_id']
            ts_str = content['timestamp']
            buffer = content['buffer']
            file_name = device_id + '_' + ts_str + '.jpg'
            status, msg = self._uploader.send_pic_buf(device_id, file_name, buffer)
            self._config.send_heartbeat(device_id, ts_str)
        if not status:
            info = json_log_build(self._config, msg)
            self._logger.error(info)

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
            camera = RaspberryCamera(self._config, width=width, height=height, rotation=rotation)
        elif GLB_SYSTEM_CAMERA == camera_type:
            camera = SystemCamera(self._config, width=width, height=height, rotation=rotation)
        elif GLB_BLUETOOTH_CAMERA == camera_type:
            camera = BleCameraController(self._config, width=width, height=height, rotation=rotation)
        return camera

    def _select_uploader(self):
        uploader_type = self._config.get_specific_attr('uploader_type')
        uploader = None
        if GLB_HTTP_UPLOADER == uploader_type:
            uploader = HttpUploader(
                self._config.get_specific_attr('app_url'))
        return uploader

    def release(self):
        self._uploader.close()


if __name__ == "__main__":
    main_loop_controller = StateController()
    main_loop_controller.execute()