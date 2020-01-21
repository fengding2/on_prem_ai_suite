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
    def __init__(self, config, width=640, height=480, rotation=0):
        self.cvlib = import_module("cv2")
        super(SystemCamera, self).__init__(width, height, rotation)
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self._logger = loggerfactory.get_logger()
        self._camera = self.cvlib.VideoCapture(0)
        self._camera.set(self.cvlib.CAP_PROP_FRAME_WIDTH, self._width)
        self._camera.set(self.cvlib.CAP_PROP_FRAME_HEIGHT, self._height)
        self._config = config

    def capture(self):
        try:
            buf = io.BytesIO()
            ret, frame = self._camera.read()
            im_rgb = self.cvlib.cvtColor(frame, self.cvlib.COLOR_BGR2RGB)
            now = datetime.now()
            img_crop_pil = Image.fromarray(im_rgb)
            img_crop_pil.save(buf, format="JPEG")
            return [{'device_id': self._config.get_device_id(), 'timestamp': str(int(now.timestamp())), 'buffer': buf.getbuffer()}]
        except Exception as e:
            self._logger.error(repr(e))
            raise e

class RaspberryCamera(AbstractCamera):
    def __init__(self, config, width=640, height=480, rotation=0):
        from picamera import PiCamera
        super(RaspberryCamera, self).__init__(width, height, rotation)
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self._logger = loggerfactory.get_logger()
        self._camera = PiCamera()
        self._camera.resolution = (self._width, self._height)
        self._camera.rotation = self._rotation
        self._config = config

    def capture(self):
        try:
            buf = io.BytesIO()
            self._camera.capture(buf, 'jpeg')
            now = datetime.now()
            return [{'device_id': self._config.get_device_id(), 'timestamp': str(int(now.timestamp())), 'buffer': buf.getbuffer()}]
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
        interval = int(self._config.get_heartbeat_interval())
        self._controller = BluetoothDongleUart(sleep_time=interval)
        self._controller.start()

    def capture(self):
        try:
            results = self._controller.capture()
            if results:
                contents = []
                for result in results:
                    device_id = result['device_id']
                    ts = result['last_timestamp']
                    stream = result['last_stream']
                    buf = io.BytesIO(stream)
                    #self._controller.flush_cache()
                    feedback = {'device_id': device_id, 'timestamp': ts, 'buffer': buf}
                    contents.append(feedback)
                return contents
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