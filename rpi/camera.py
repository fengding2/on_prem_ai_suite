from imports import *
import abc
import io
from datetime import datetime
from PIL import Image
import time
from importlib import import_module


class AbstractCamera(abc.ABC):
    def __init__(self, width, height, rotation):
        self._width = width
        self._height = height
        self._rotation = rotation

    """
    camera capture pictures
    return (timestamp, binary_buffer)
    """
    @abc.abstractmethod
    def capture(self):
        pass

class SystemCamera(AbstractCamera):
    def __init__(self, width=640, height=480, rotation=0):
        self.cvlib = import_module("cv2")
        super(SystemCamera, self).__init__(width, height, rotation)
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self._logger = loggerfactory.get_logger()
        self._camera = self.cvlib.VideoCapture(0)
        self._camera.set(self.cvlib.CAP_PROP_FRAME_WIDTH, self._width)
        self._camera.set(self.cvlib.CAP_PROP_FRAME_HEIGHT, self._height)

    def capture(self):
        try:
            buf = io.BytesIO()
            ret, frame = self._camera.read()
            im_rgb = self.cvlib.cvtColor(frame, self.cvlib.COLOR_BGR2RGB)
            now = datetime.now()
            img_crop_pil = Image.fromarray(im_rgb)
            img_crop_pil.save(buf, format="JPEG")
            return str(int(now.timestamp())), buf.getbuffer()
        except Exception as e:
            self._logger.error(repr(e))
            raise e

class RaspberryCamera(AbstractCamera):
    def __init__(self, width=640, height=480, rotation=0):
        from picamera import PiCamera
        super(RaspberryCamera, self).__init__(width, height, rotation)
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self._logger = loggerfactory.get_logger()
        self._camera = PiCamera()
        self._camera.resolution = (self._width, self._height)
        self._camera.rotation = self._rotation

    def capture(self):
        try:
            buf = io.BytesIO()
            self._camera.capture(buf, 'jpeg')
            now = datetime.now()
            return str(int(now.timestamp())), buf.getbuffer()
        except Exception as e:
            self._logger.error(repr(e))
            raise e

class BleCameraController(AbstractCamera):
    def __init__(self, config, width=640, height=480, rotation=0):
        from bluetooth_dongle_uart import BluetoothDongleUart
        super(BleCameraController, self).__init__(width, height, rotation)
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self._config = config
        self._logger = loggerfactory.get_logger()
        self._controller = BluetoothDongleUart()
        self._controller.start()

    def capture(self):
        try:
            results = self._controller.capture()
            if results:
                device = results[0]
                device_id = device['device_id']
                ts = device['last_timestamp']
                stream = device['last_stream']
                has_registered = device['has_registered']
                if not has_registered:
                    state = self._config.register_device(device_id, active_heartbeat=False)
                    if state:
                        self._controller.set_registered(device_id)
                        self._config.start()

                self._config.set_heartbeat(device_id, ts)
                buf = io.BytesIO(stream)
                self._controller.flush_cache()
                if stream:
                    return ts, buf.getvalue()
                else:
                    raise RuntimeError("capture no data")
            else:
                raise RuntimeError("capture no any feedback")
        except Exception as e:
            self._logger.error(repr(e))
            raise e

class CameraUtil():
    def __init__(self, camera):
        self._camera = camera

    def save_one_pic(self, file_name):
        _, buf = self._camera.capture()
        image = Image.open(io.BytesIO(buf))
        image.save(file_name)

    def save_five_pic_per_5second(self, file_prefix):
        for i in range(5):
            _, buf = self._camera.capture()
            image = Image.open(io.BytesIO(buf))
            file_path = file_prefix + str(i) + '.jpg'
            image.save(file_path)
            time.sleep(5)


if __name__ == "__main__":
    camera = SystemCamera()
    print("initial the camera...")
    util = CameraUtil(camera)
    time.sleep(10)
    print("start to capture...")
    util.save_five_pic_per_5second("t_")